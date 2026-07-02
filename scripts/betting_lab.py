#!/usr/bin/env python3
"""
@file    betting_lab.py
@brief   多数の「買い方」を ウォークフォワード で検証し、安定して回収率の高い戦略を探す
@version 1.0.0  2026-06-28  (Dicky1114)

予測 = 市場ブレンド(c=Benter 2段)で各馬の勝率→レース内順位。
各foldの未来ブロックで各戦略の回収率を計算し、fold間の平均/ばらつき/勝率を見る。
1回の100%超はノイズ。**複数foldで安定して>100%** のみ本物候補。

券種払戻列: pay1(単勝) pay123_1/2/3(複勝) pay12_21(馬連) pay12_12(馬単)
            pay123_321(3連複) pay123_123(3連単)  ※ワイドは未取得
使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/betting_lab.py
"""
import os, sys, logging, warnings
from itertools import permutations, combinations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scripts.run_roi_analysis import load_data
from scripts.market_blend import fundamental_features, fit_blend, softmax_by_race, GROUP_COLS, EPS
from scripts.science_menu import prep
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
N_FOLDS = 5
UNIT = 100
WIDE = {}  # (race_id, (h_a,h_b)) -> payout  (h_a<h_b)  ※当たり3組のみ存在


def load_wide():
    path = os.path.join(BASE_DIR, 'media', 'csv_export', 'wide_payouts.csv')
    if not os.path.exists(path):
        return
    w = pd.read_csv(path, dtype={'race_id': str})
    for _, r in w.iterrows():
        WIDE[(r['race_id'], (int(r['h_a']), int(r['h_b'])))] = float(r['payout'])


def wpay(rid, h, k):
    return WIDE.get((rid, tuple(sorted([int(h), int(k)]))), 0.0)


def predict_c(df, X, A, B):
    import lightgbm as lgb
    m = lgb.LGBMClassifier(objective='binary', n_estimators=400, learning_rate=0.03, num_leaves=31,
        max_depth=5, min_child_samples=30, subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
        random_state=42, n_jobs=-1, verbosity=-1)
    m.fit(X.values[A], df['is_win'].values[A])
    d = df.copy(); d['f_raw'] = m.predict_proba(X.values)[:, 1]
    d['f_norm'] = softmax_by_race(d.assign(_lf=np.log(np.clip(d['f_raw'], EPS, 1))), '_lf')
    a, b = fit_blend(d[B])
    d['z'] = a*np.log(np.clip(d['f_norm'], EPS, 1)) + b*np.log(np.clip(d['pi'], EPS, 1))
    d['c'] = softmax_by_race(d, 'z')
    return d


def race_info(g):
    """1レースの予測上位・実結果・払戻を返す。"""
    g = g.sort_values('c', ascending=False)
    top = [str(x) for x in g['horse_number'].tolist()]
    ctop = g['c'].tolist()
    a1 = g[g['rank_int'] == 1]['horse_number']
    a2 = g[g['rank_int'] == 2]['horse_number']
    a3 = g[g['rank_int'] == 3]['horse_number']
    if len(a1) == 0 or len(a2) == 0 or len(a3) == 0:
        return None
    def pay(col):
        v = pd.to_numeric(g[col], errors='coerce').dropna()
        return float(v.iloc[0]) if len(v) else 0.0
    return {
        'rid': g['race_id'].iloc[0],
        'top': top, 'ctop': ctop,
        'a1': str(a1.iloc[0]), 'a2': str(a2.iloc[0]), 'a3': str(a3.iloc[0]),
        'fav': str(g.sort_values('odds')['horse_number'].iloc[0]),
        'pay1': pay('pay1'), 'fuku': {str(g[g['rank_int']==r]['horse_number'].iloc[0]): pay(c)
                  for r, c in [(1,'pay123_1'),(2,'pay123_2'),(3,'pay123_3')]},
        'umaren': pay('pay12_21'), 'umatan': pay('pay12_12'),
        'sanfuku': pay('pay123_321'), 'santan': pay('pay123_123'),
        'odds_top1': g.sort_values('c', ascending=False)['odds'].iloc[0],
    }


# 各戦略: (bet点数, 払戻) を返す関数。買わない場合は(0,0)。
def strategies(r):
    out = {}
    top, a1, a2, a3 = r['top'], r['a1'], r['a2'], r['a3']
    c0 = r['ctop'][0]
    s = set
    # 単勝
    out['単勝_top1'] = (1, r['pay1'] if top[0]==a1 else 0)
    out['単勝_top1_確信>20%'] = (1, r['pay1'] if top[0]==a1 else 0) if c0>0.20 else (0,0)
    out['単勝_top1_オッズ3-10'] = (1, r['pay1'] if top[0]==a1 else 0) if 3<=r['odds_top1']<10 else (0,0)
    # 複勝
    out['複勝_top1'] = (1, r['fuku'].get(top[0],0) if top[0] in {a1,a2,a3} else 0)
    out['複勝_top2'] = (2, sum(r['fuku'].get(h,0) for h in top[:2] if h in {a1,a2,a3}))
    out['複勝_top3'] = (3, sum(r['fuku'].get(h,0) for h in top[:3] if h in {a1,a2,a3}))
    out['複勝_人気1'] = (1, r['fuku'].get(r['fav'],0) if r['fav'] in {a1,a2,a3} else 0)
    # ワイド (2頭とも3着以内で的中・低分散)
    rid = r['rid']; top3set = {a1,a2,a3}
    out['ワイド_top2'] = (1, wpay(rid, top[0], top[1]) if (top[0] in top3set and top[1] in top3set) else 0)
    wb = 0
    for x, y in combinations(top[:3], 2):
        if x in top3set and y in top3set:
            wb += wpay(rid, x, y)
    out['ワイド_top3BOX'] = (3, wb)
    wf = 0
    for y in top[1:4]:
        if top[0] in top3set and y in top3set:
            wf += wpay(rid, top[0], y)
    out['ワイド_1着軸流top2-4'] = (3, wf)
    # 馬連/馬単
    out['馬連_top2'] = (1, r['umaren'] if s(top[:2])=={a1,a2} else 0)
    out['馬連_top3BOX'] = (3, r['umaren'] if s([a1,a2])<=s(top[:3]) else 0)
    out['馬単_top1→2'] = (1, r['umatan'] if top[0]==a1 and top[1]==a2 else 0)
    out['馬単_1着固定流top2-3'] = (2, r['umatan'] if top[0]==a1 and a2 in top[1:3] else 0)
    # 馬単 top3 全順列BOX(6点): 1-2,2-1,1-3,3-1,2-3,3-2 を全部買う
    out['馬単_top3BOX(6点)'] = (6, r['umatan'] if (a1 in s(top[:3]) and a2 in s(top[:3])) else 0)
    # 馬単 top2 全順列BOX(2点): 1-2,2-1
    out['馬単_top2BOX(2点)'] = (2, r['umatan'] if (a1 in s(top[:2]) and a2 in s(top[:2])) else 0)
    # 3連単 top3 全順列BOX(6点)
    out['3連単_top3BOX(6点)'] = (6, r['santan'] if s(top[:3])=={a1,a2,a3} else 0)
    # 3連単 1着固定→2,3着top2-4流し(全順列・確信ゲート無し)
    f234b = top[1:4]
    out['3連単_1着固定2-3流(6点)無ゲート'] = (6, r['santan'] if (top[0]==a1 and a2 in f234b and a3 in f234b and a2!=a3) else 0)
    # 3連複
    out['3連複_top3BOX'] = (1, r['sanfuku'] if s(top[:3])=={a1,a2,a3} else 0)
    out['3連複_top4BOX'] = (4, r['sanfuku'] if s([a1,a2,a3])<=s(top[:4]) else 0)
    out['3連複_top5BOX'] = (10, r['sanfuku'] if s([a1,a2,a3])<=s(top[:5]) else 0)
    # 3連単(確信度ゲート: top1勝率が高い時のみ)
    # 1着固定top1 → 2,3着 top2-4 流し(6点)
    f234 = top[1:4]
    hit_form = (top[0]==a1 and a2 in f234 and a3 in f234 and a2!=a3)
    out['3連単_1着固定_2-3流(6点)'] = (6, r['santan'] if hit_form else 0) if c0>0.25 else (0,0)
    out['3連単_top3BOX_確信>30%'] = (6, r['santan'] if [top[0],top[1],top[2]] and s(top[:3])=={a1,a2,a3} and (top[0]==a1 and top[1]==a2 and top[2]==a3) else 0) if c0>0.30 else (0,0)
    return out


TOT_BET, TOT_RET, TOT_HIT, PTS = {}, {}, {}, {}


def main():
    load_wide()
    logger.info(f"ワイド払戻ロード: {len(WIDE)}件")
    df = prep(load_data())
    X, feat = fundamental_features(df)
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races); start = int(n*0.4); block = (n-start)//N_FOLDS
    logger.info(f"{n}レース / 特徴量{len(feat)} / {N_FOLDS}fold")

    fold_roi = {}   # strategy -> list of fold ROI
    fold_n = {}
    for k in range(N_FOLDS):
        tr_end = start + k*block; te_end = start+(k+1)*block if k<N_FOLDS-1 else n
        tl = races[:tr_end]; cut = int(len(tl)*0.7)
        A = df['race_id'].isin(set(tl[:cut])).values
        B = df['race_id'].isin(set(tl[cut:])).values
        test_ids = set(races[tr_end:te_end])
        d = predict_c(df, X, A, B)
        t = d[d['race_id'].isin(test_ids)]
        agg = {}  # strat -> [bet, ret, nbet]
        for rid, g in t.groupby('race_id'):
            ri = race_info(g)
            if ri is None:
                continue
            for name, (pts, ret) in strategies(ri).items():
                if pts == 0:
                    continue
                a = agg.setdefault(name, [0, 0, 0])
                a[0] += pts*UNIT; a[1] += ret; a[2] += 1
                PTS[name] = pts
                if ret > 0:
                    TOT_HIT[name] = TOT_HIT.get(name, 0) + 1
        for name, (bet, ret, nb) in agg.items():
            roi = ret/bet*100 if bet else float('nan')
            fold_roi.setdefault(name, []).append(roi)
            fold_n[name] = fold_n.get(name, 0) + nb
            TOT_BET[name] = TOT_BET.get(name, 0) + bet
            TOT_RET[name] = TOT_RET.get(name, 0) + ret

    print("\n" + "="*100)
    print("  買い方ラボ: ウォークフォワード回収率 (複数foldで安定>100%のみ本物)")
    print("="*100)
    print(f"  {'戦略':<26}{'平均回収率':>9}{'σ':>7}{'>100%fold':>10}{'購入レース':>9}  fold別回収率")
    print("-"*100)
    rows = []
    for name, rois in fold_roi.items():
        arr = np.array([r for r in rois if not np.isnan(r)])
        if len(arr) == 0:
            continue
        prof = int((arr > 100).sum())
        rows.append((name, arr.mean(), arr.std(), prof, len(arr), fold_n.get(name,0), arr))
    rows.sort(key=lambda x: -x[1])
    for name, mean, std, prof, nf, nb, arr in rows:
        mark = '✅' if (prof >= N_FOLDS-1 and mean > 100) else ('△' if prof >= 3 else '')
        print(f"  {name:<26}{mean:>8.1f}%{std:>7.0f}{prof:>7}/{nf}{nb:>9}  [{' '.join(f'{x:.0f}' for x in arr)}] {mark}")
    print("="*100)
    print("  ※ ✅=複数foldで安定>100%(本物候補) / 平均>100%でもσ大・単発なら罠")

    # 実データ(円)で集計出力 → CSV
    recs = []
    for name in TOT_BET:
        bet = TOT_BET[name]; ret = int(TOT_RET[name]); nb = fold_n.get(name, 0)
        hit = TOT_HIT.get(name, 0)
        recs.append({
            '戦略': name, '点数/レース': PTS.get(name, 1), '購入レース数': nb,
            '総投資(円)': bet, '総回収(円)': ret, '損益(円)': ret - bet,
            '的中数': hit, '的中率(%)': round(hit / nb * 100, 1) if nb else 0,
            '回収率(%)': round(ret / bet * 100, 1) if bet else 0,
        })
    rdf = pd.DataFrame(recs).sort_values('回収率(%)', ascending=False)
    out = os.path.join(BASE_DIR, 'media', 'csv_export', 'betting_results_yen.csv')
    rdf.to_csv(out, index=False)
    print("\n  === 実データ(円)集計 ===")
    print(rdf.to_string(index=False))
    print(f"\n  CSV: {out}")


if __name__ == '__main__':
    main()
