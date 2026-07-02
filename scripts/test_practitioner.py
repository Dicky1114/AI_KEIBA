#!/usr/bin/env python3
"""
@file    test_practitioner.py
@brief   実践者の買い方(累乗鋭利化+期待値ゲート+EV差ゲート+no-bet)をウォークフォワード検証
@version 1.0.0  2026-06-29 (Dicky1114)

勝者の核心(リサーチ): 予測でなく"買い方フィルタ"。
  1) 較正済み勝率 p を累乗で鋭利化: p_s = p^k / Σ(p^k)
  2) 期待値 EV = p_s × 単勝オッズ
  3) EV最大馬の EV>=th かつ (EV1位-EV2位)>=gap のレースだけ単勝購入(no-bet多用)
⚠️ 確定オッズ使用=未来リーク(実運用不可)。それでも勝てるか/勝てないかを見る。
"""
import os, sys, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scripts.run_roi_analysis import load_data
from scripts.market_blend import fundamental_features, GROUP_COLS
from scripts.science_menu import prep
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
N_FOLDS = 5
UNIT = 100


def fold_predict(df, X, A, B):
    """A学習→B較正(isotonic)→全体の較正済み勝率 p。"""
    import lightgbm as lgb
    from sklearn.isotonic import IsotonicRegression
    m = lgb.LGBMClassifier(objective='binary', n_estimators=400, learning_rate=0.03, num_leaves=31,
        max_depth=5, min_child_samples=30, subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
        random_state=42, n_jobs=-1, verbosity=-1)
    m.fit(X.values[A], df['is_win'].values[A])
    raw = m.predict_proba(X.values)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(raw[B], df['is_win'].values[B])
    return iso.transform(raw)


def simulate(t, k, th, gap):
    """t: test df(p,odds,rank_int,pay1). 累乗鋭利化+EVゲート+EV差ゲートで単勝。"""
    bet = ret = hit = nb = nraces = 0
    for rid, g in t.groupby('race_id'):
        nraces += 1
        p = g['p'].to_numpy(float)
        ps = p ** k
        s = ps.sum()
        if s <= 0:
            continue
        ps = ps / s
        odds = g['odds'].to_numpy(float)
        ev = ps * odds
        order = np.argsort(-ev)
        ev1 = ev[order[0]]
        ev2 = ev[order[1]] if len(order) > 1 else 0.0
        if ev1 < th or (ev1 - ev2) < gap:
            continue  # no-bet
        row = g.iloc[order[0]]
        bet += UNIT; nb += 1
        if int(row['rank_int']) == 1:
            pv = pd.to_numeric(g['pay1'], errors='coerce').dropna()
            ret += float(pv.iloc[0]) if len(pv) else 0
            hit += 1
    roi = ret / bet * 100 if bet else float('nan')
    return roi, nb, hit, nraces


def main():
    df = prep(load_data())
    df['target_time'] = 0  # placeholder
    X, feat = fundamental_features(df)
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races); start = int(n * 0.4); block = (n - start) // N_FOLDS

    # 各fold予測を準備
    folds = []
    for kf in range(N_FOLDS):
        tr_end = start + kf * block; te_end = start + (kf + 1) * block if kf < N_FOLDS - 1 else n
        tl = races[:tr_end]; cut = int(len(tl) * 0.7)
        A = df['race_id'].isin(set(tl[:cut])).values
        B = df['race_id'].isin(set(tl[cut:])).values
        T = df['race_id'].isin(set(races[tr_end:te_end])).values
        p = fold_predict(df, X, A, B)
        d = df.copy(); d['p'] = p
        folds.append(d[T].copy())

    print("\n" + "=" * 92)
    print("  実践者の買い方(累乗鋭利化+EVゲート+EV差ゲート+no-bet) ウォークフォワード")
    print("  ※確定オッズ使用=未来リーク有。勝てなければ完全終了/勝てたらリーク要因")
    print("=" * 92)
    print(f"  {'k(鋭利化)':>8}{'EV閾値':>7}{'EV差':>6}  fold別回収率(購入レース率)        平均回収率")
    print("-" * 92)
    for k in [1, 2, 4]:
        for th, gap in [(1.0, 0.0), (1.1, 0.0), (1.1, 0.4), (1.3, 0.5)]:
            rois, bets, races_bet = [], 0, 0
            tot_races = 0
            for d in folds:
                roi, nb, hit, nr = simulate(d, k, th, gap)
                rois.append(roi); bets += nb; races_bet += nb; tot_races += nr
            arr = np.array([r for r in rois if not np.isnan(r)])
            if len(arr) == 0:
                print(f"  {k:>8}{th:>7.1f}{gap:>6.1f}  (購入0)")
                continue
            betrate = bets / tot_races * 100
            mark = '✅' if (arr > 100).sum() >= N_FOLDS - 1 and arr.mean() > 100 else ('△' if (arr > 100).sum() >= 3 else '❌')
            print(f"  {k:>8}{th:>7.1f}{gap:>6.1f}  [{' '.join(f'{x:3.0f}' for x in arr)}] 購入{betrate:4.0f}%  {arr.mean():6.1f}% {mark}")
    print("=" * 92)
    print("  ※ ✅=複数foldで安定>100% / 購入%=全レース中どれだけ買ったか(低い=no-bet多)")


if __name__ == '__main__':
    main()
