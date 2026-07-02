#!/usr/bin/env python3
"""
@file    betting_lab_value.py
@brief   券種ごとに論理を変えた「価値(value)意識」買い方をウォークフォワード検証
@version 1.0.0  2026-06-30  (Dicky1114)

設計思想(プロの券種別ロジック):
  ・単勝/複勝 = 的中率ゲー → 高確信(本命)を厚く取る。外れにくい所だけ買う。
  ・馬連/馬単/3連複/3連単 = 配当ゲー → 高オッズを狙う。
       「スコアが市場と一致しすぎ(=全部人気・オッズ低)」の組は当たっても安く旨味ゼロ→買わない。
       モデルは上位に見るが市場は軽視(高オッズ)の馬を絡めた時だけ妙味。
  ・上位1頭だけでなく、モデル2-4位を相手に流す/BOXで複数頭を取る。

  予測 = betting_lab と同じ Benter 2段ブレンド c。5fold ウォークフォワード。
  単一splitの上振れを排除するため fold別ROIとσ・>100%fold数で判定する。

用語:
  axis_solid : 軸(モデル1位)が信頼できる = 確信c0>=AXIS_C かつ 単勝オッズ<=AXIS_ODDS
  value_leg  : モデルが上位に見るのに単勝オッズ>=VALUE_ODDS の「市場が軽視する妙味馬」
  too_chalk  : 選んだ相手が全員オッズ<CHALK_ODDS = 固すぎ→exoticは買わない

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/betting_lab_value.py
"""
import os, sys, logging, warnings
from itertools import combinations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import django  # noqa
django.setup()

from scripts.run_roi_analysis import load_data
from scripts.market_blend import fundamental_features, fit_blend, softmax_by_race, GROUP_COLS, EPS
from scripts.science_menu import prep
from scripts.betting_lab import predict_c

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
N_FOLDS = 5
UNIT = 100
# 価値判定のしきい値
AXIS_C = 0.22       # 軸の最低確信
AXIS_ODDS = 4.0     # 軸の最高オッズ(これ以下なら軸として信頼)
VALUE_ODDS = 5.0    # 妙味馬の最低オッズ
CHALK_ODDS = 3.0    # これ未満ばかりなら固すぎ


def race_info(g):
    """モデル順(c降順)の馬番・オッズ・確信、実着順、払戻を返す。"""
    g = g.sort_values('c', ascending=False)
    top = [str(x) for x in g['horse_number'].tolist()]
    odds = [float(x) for x in g['odds'].tolist()]
    ctop = [float(x) for x in g['c'].tolist()]
    a1 = g[g['rank_int'] == 1]['horse_number']
    a2 = g[g['rank_int'] == 2]['horse_number']
    a3 = g[g['rank_int'] == 3]['horse_number']
    if len(a1) == 0 or len(a2) == 0 or len(a3) == 0:
        return None

    def pay(col):
        v = pd.to_numeric(g[col], errors='coerce').dropna()
        return float(v.iloc[0]) if len(v) else 0.0
    od = {h: o for h, o in zip(top, odds)}
    return {
        'rid': g['race_id'].iloc[0], 'top': top, 'odds': od, 'c': ctop,
        'a1': str(a1.iloc[0]), 'a2': str(a2.iloc[0]), 'a3': str(a3.iloc[0]),
        'pay1': pay('pay1'),
        'fuku': {str(g[g['rank_int'] == r]['horse_number'].iloc[0]): pay(c)
                 for r, c in [(1, 'pay123_1'), (2, 'pay123_2'), (3, 'pay123_3')]},
        'umaren': pay('pay12_21'), 'umatan': pay('pay12_12'),
        'sanfuku': pay('pay123_321'), 'santan': pay('pay123_123'),
    }


def strategies(r):
    """各戦略 -> (点数, 払戻). 買わない=(0,0)."""
    out = {}
    top, od, c = r['top'], r['odds'], r['c']
    a1, a2, a3 = r['a1'], r['a2'], r['a3']
    res3 = {a1, a2, a3}
    c0 = c[0]
    o0 = od[top[0]]
    axis_solid = (c0 >= AXIS_C and o0 <= AXIS_ODDS)

    # ===== 単勝・複勝 = 的中率ゲー: 高確信の本命を取る =====
    out['単勝_本命のみ(c>=.35&o<=3)'] = (
        (1, r['pay1'] if top[0] == a1 else 0) if (c0 >= 0.35 and o0 <= 3.0) else (0, 0))
    out['複勝_本命1点(c>=.30)'] = (
        (1, r['fuku'].get(top[0], 0) if top[0] in res3 else 0) if c0 >= 0.30 else (0, 0))
    out['複勝_本命厚(c>=.40)'] = (
        (1, r['fuku'].get(top[0], 0) if top[0] in res3 else 0) if c0 >= 0.40 else (0, 0))
    # top2複勝(的中率さらに上げる・2点)
    out['複勝_top2(c>=.30)'] = (
        (2, sum(r['fuku'].get(h, 0) for h in top[:2] if h in res3)) if c0 >= 0.30 else (0, 0))

    # ===== 馬連 = 配当: 軸固い + 相手に妙味馬 =====
    # 1着軸(top1)流し: 相手 = モデルtop2-5 のうち オッズ>=VALUE のみ(妙味). 軸が固い時だけ.
    if axis_solid:
        legs = [h for h in top[1:6] if od[h] >= VALUE_ODDS]
        if legs:
            # 流し馬連: 買い目 = {(軸, 相手)}. 的中 = 軸が1or2着 かつ もう片方が相手内.
            pair = {a1, a2}
            other = pair - {top[0]}
            hit = r['umaren'] if (top[0] in pair and len(other) == 1
                                  and next(iter(other)) in set(legs)) else 0
            out['馬連_本命軸-妙味流し'] = (len(legs), hit)
        else:
            out['馬連_本命軸-妙味流し'] = (0, 0)
    else:
        out['馬連_本命軸-妙味流し'] = (0, 0)
    # 比較: 単純 top2BOX だが 固すぎ(両頭<CHALK)はskip
    pair = top[:2]
    if max(od[pair[0]], od[pair[1]]) >= CHALK_ODDS:  # 少なくとも片方は人気薄=妙味
        out['馬連_top2_非チャラ'] = (1, r['umaren'] if {a1, a2} == set(pair) else 0)
    else:
        out['馬連_top2_非チャラ'] = (0, 0)

    # ===== 3連複 = 配当: top4/5 BOX だが 妙味馬を含む時のみ =====
    box4 = top[:4]
    has_value4 = any(od[h] >= VALUE_ODDS for h in box4)
    if has_value4:
        out['3連複_top4BOX_妙味込'] = (4, r['sanfuku'] if {a1, a2, a3} <= set(box4) else 0)
    else:
        out['3連複_top4BOX_妙味込'] = (0, 0)
    box5 = top[:5]
    if any(od[h] >= VALUE_ODDS for h in box5):
        out['3連複_top5BOX_妙味込'] = (10, r['sanfuku'] if {a1, a2, a3} <= set(box5) else 0)
    else:
        out['3連複_top5BOX_妙味込'] = (0, 0)
    # 軸1頭(本命)固定 - 相手top2-5から2頭(妙味優先)
    if axis_solid:
        partners = top[1:6]
        if len(partners) >= 2:
            # 軸 + 相手2頭の組合せ全部(BOX的) 点数=C(len,2)
            combos = list(combinations(partners, 2))
            pts = len(combos)
            hit = 0
            for x, y in combos:
                if {a1, a2, a3} == {top[0], x, y}:
                    hit = r['sanfuku']; break
            # 固すぎ(相手全員<CHALK)はskip
            if any(od[h] >= CHALK_ODDS for h in partners):
                out['3連複_本命軸-相手流し'] = (pts, hit)
            else:
                out['3連複_本命軸-相手流し'] = (0, 0)
        else:
            out['3連複_本命軸-相手流し'] = (0, 0)
    else:
        out['3連複_本命軸-相手流し'] = (0, 0)

    # ===== 3連単 = 高配当: 1着固定(固い本命) → 2,3着 妙味流し =====
    if axis_solid and top[0] == top[0]:
        legs = top[1:5]  # 2,3着候補 = モデル2-4位
        if any(od[h] >= CHALK_ODDS for h in legs):  # 相手に妙味あり
            # 1着=top0固定, 2-3着= legs から順列(点数 = P(len,2))
            pts = len(legs) * (len(legs) - 1)
            hit = r['santan'] if (a1 == top[0] and a2 in legs and a3 in legs and a2 != a3) else 0
            out['3連単_本命1着固定-妙味流し'] = (pts, hit)
        else:
            out['3連単_本命1着固定-妙味流し'] = (0, 0)
    else:
        out['3連単_本命1着固定-妙味流し'] = (0, 0)

    # 参考: 3連複 top3BOX を 固すぎskip 付き(=妙味top3だけ)
    box3 = top[:3]
    if any(od[h] >= VALUE_ODDS for h in box3):
        out['3連複_top3_妙味のみ'] = (1, r['sanfuku'] if {a1, a2, a3} == set(box3) else 0)
    else:
        out['3連複_top3_妙味のみ'] = (0, 0)
    return out


def main():
    df = prep(load_data())
    X, feat = fundamental_features(df)
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races); start = int(n * 0.4); block = (n - start) // N_FOLDS
    logger.info(f"{n}レース 特徴量{len(feat)} {N_FOLDS}fold  "
                f"AXIS_C={AXIS_C} AXIS_ODDS={AXIS_ODDS} VALUE_ODDS={VALUE_ODDS}")

    fold_roi, fold_n, TOT_BET, TOT_RET, TOT_HIT, PTS = {}, {}, {}, {}, {}, {}
    for k in range(N_FOLDS):
        tr_end = start + k * block; te_end = start + (k + 1) * block if k < N_FOLDS - 1 else n
        tl = races[:tr_end]; cut = int(len(tl) * 0.7)
        A = df['race_id'].isin(set(tl[:cut])).values
        B = df['race_id'].isin(set(tl[cut:])).values
        test_ids = set(races[tr_end:te_end])
        d = predict_c(df, X, A, B)
        t = d[d['race_id'].isin(test_ids)]
        agg = {}
        for rid, g in t.groupby('race_id'):
            ri = race_info(g)
            if ri is None:
                continue
            for name, (pts, ret) in strategies(ri).items():
                if pts == 0:
                    continue
                a = agg.setdefault(name, [0, 0, 0])
                a[0] += pts * UNIT; a[1] += ret; a[2] += 1
                PTS[name] = pts
                if ret > 0:
                    TOT_HIT[name] = TOT_HIT.get(name, 0) + 1
        for name, (bet, ret, nb) in agg.items():
            roi = ret / bet * 100 if bet else float('nan')
            fold_roi.setdefault(name, []).append(roi)
            fold_n[name] = fold_n.get(name, 0) + nb
            TOT_BET[name] = TOT_BET.get(name, 0) + bet
            TOT_RET[name] = TOT_RET.get(name, 0) + ret

    print("\n" + "=" * 104)
    print("  券種別・価値意識 買い方ラボ: ウォークフォワード回収率(複数foldで安定>100%のみ本物)")
    print("=" * 104)
    print(f"  {'戦略':<30}{'平均ROI':>8}{'σ':>6}{'>100fold':>9}{'購入R':>7}{'的中率':>7}  fold別ROI")
    print("-" * 104)
    rows = []
    for name, rois in fold_roi.items():
        arr = np.array([x for x in rois if not np.isnan(x)])
        if len(arr) == 0:
            continue
        prof = int((arr > 100).sum())
        nb = fold_n.get(name, 0); hit = TOT_HIT.get(name, 0)
        hr = hit / nb * 100 if nb else 0
        rows.append((name, arr.mean(), arr.std(), prof, len(arr), nb, hr, arr))
    rows.sort(key=lambda x: -x[1])
    for name, mean, std, prof, nf, nb, hr, arr in rows:
        mark = '✅' if (prof >= N_FOLDS - 1 and mean > 100) else ('△' if prof >= 3 else '')
        fl = ' '.join(f'{x:.0f}' for x in arr)
        print(f"  {name:<30}{mean:>7.0f}%{std:>6.0f}{prof:>6}/{nf}{nb:>7}{hr:>6.1f}%  [{fl}] {mark}")
    print("=" * 104)
    print("  ✅=安定>100(本物候補) △=3fold以上>100  単複は的中率/3連系は配当の妥当性も見る")


if __name__ == '__main__':
    main()
