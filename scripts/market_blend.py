#!/usr/bin/env python3
"""
@file    market_blend.py
@brief   Benter式 市場ブレンド(2段conditional logit) + ΔR² Go/No-Go + オッズ帯別バリュー
@version 1.0.0  2026-06-28  新規作成 (Dicky1114)

リサーチ結論の実装(競馬予測ML最適化調査):
  - 1段目(ファンダ)モデル f_i は **オッズ/人気を入れず** に学習(市場のコピー化を防ぐ)。
  - 市場確率 π_i = (1/odds)/Σ(1/odds)  (オーバーラウンド除去)。
  - 2段目: c_i = softmax_race( α·log f_i + β·log π_i ) の α,β を winner の対数尤度最大化で推定。
  - **Go/No-Go = ブレンド c が 市場単独 π を logloss で上回るか(ΔLL>0)**。
    これが＋でなければ、どんな賭け方でも理論上負ける(=賭ける価値なし)。
  - リーク防止: ファンダ f は学習に使っていないデータ(out-of-sample)で作る。

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/market_blend.py
"""

import os
import sys
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import numpy as np
import pandas as pd

from scripts.run_roi_analysis import load_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

GROUP_COLS = ['today_race_date', 'race_id']
RESULT_COLS = ['rank', 'race_time', 'corner_order', 'last_3f', 'margin',
               'positions', 'positions_tie',
               'pay1', 'pay1_tie', 'pay123_1', 'pay123_2', 'pay123_3',
               'pay12_21', 'pay12_12', 'pay123_321', 'pay123_123']
# 1段目(ファンダ)から除外する“市場由来”特徴(=2段目でのみ使う)
# WHY: prev_odds / prev_popularity は過去の市場評価=市場のコピー。
#      アブレーションで「履歴群除外がΔLL改善」=市場コピーが増分情報を薄めると判明したため、
#      1段目からは外し、市場情報は2段目ブレンド(π)に一本化する。
MARKET_COLS = ['odds', 'popularity', 'implied_prob', 'prev_odds', 'prev_popularity']
EPS = 1e-9


def softmax_by_race(df, value_col, race_col='race_id'):
    def _f(s):
        s = s - s.max()
        e = np.exp(s)
        return e / e.sum()
    return df.groupby(race_col)[value_col].transform(_f)


def fundamental_features(df):
    # WHY: pi/inv_odds(=市場確率)・target_time(=答えのタイム)・各種派生列は
    #      1段目に絶対入れない(市場/結果のリーク=ΔLLを偽って改善させる)。
    LEAK = ['pi', 'inv_odds', 'target_time', 'score', 'f_raw', 'f_norm', 'z', 'c', 'f_blend']
    exclude = set(RESULT_COLS + GROUP_COLS + MARKET_COLS + ['horse_number', 'rank_int', 'is_win', 'id'] + LEAK)
    feat = [c for c in df.columns if c not in exclude]
    X = df[feat].copy()
    for c in X.columns:
        if X[c].dtype == 'object':
            X[c] = X[c].astype('category').cat.codes
        else:
            X[c] = pd.to_numeric(X[c], errors='coerce')
    return X.fillna(-1).astype('float32'), feat


def winner_logloss(df, prob_col):
    """各レースの実勝ち馬に割り当てた確率の -logの平均(小さいほど良)。"""
    lls = []
    for _, g in df.groupby('race_id'):
        w = g[g['rank_int'] == 1]
        if len(w) == 0:
            continue
        p = float(w.iloc[0][prob_col])
        lls.append(-np.log(max(p, EPS)))
    return float(np.mean(lls)) if lls else float('nan')


def fit_blend(df_calib):
    """α,β を winner対数尤度最大化で推定(scipy)。"""
    from scipy.optimize import minimize
    logf = np.log(np.clip(df_calib['f_norm'].values, EPS, 1))
    logpi = np.log(np.clip(df_calib['pi'].values, EPS, 1))
    race = df_calib['race_id'].values
    is_win = (df_calib['rank_int'].values == 1).astype(float)
    races = pd.unique(race)
    idx = {r: np.where(race == r)[0] for r in races}

    def negll(params):
        a, b = params
        z = a * logf + b * logpi
        total = 0.0
        for r in races:
            ii = idx[r]
            zz = z[ii] - z[ii].max()
            e = np.exp(zz)
            p = e / e.sum()
            w = is_win[ii]
            if w.sum() > 0:
                total += np.log(max((p * w).sum(), EPS))
        return -total

    res = minimize(negll, x0=[1.0, 1.0], method='Nelder-Mead')
    return float(res.x[0]), float(res.x[1])


def main():
    import lightgbm as lgb

    df = load_data()
    df['rank_int'] = pd.to_numeric(df['rank'], errors='coerce')
    df['is_win'] = (df['rank_int'] == 1).astype(int)
    df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
    df = df[df['odds'] > 0].copy()

    # 市場確率 π (オーバーラウンド除去)
    df['inv_odds'] = 1.0 / df['odds']
    df['pi'] = df.groupby('race_id')['inv_odds'].transform(lambda s: s / s.sum())

    # 時系列split: trainA(ファンダ学習) / trainB(ブレンド較正) / test(評価)
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)
    n = len(races)
    n_test = int(n * 0.2)
    n_calib = int(n * 0.2)
    test_ids = set(races.iloc[n - n_test:]['race_id'])
    calib_ids = set(races.iloc[n - n_test - n_calib:n - n_test]['race_id'])
    trainA_ids = set(races.iloc[:n - n_test - n_calib]['race_id'])
    A = df['race_id'].isin(trainA_ids).values
    B = df['race_id'].isin(calib_ids).values
    T = df['race_id'].isin(test_ids).values
    logger.info(f"trainA={A.sum()}行 calib={B.sum()}行 test={T.sum()}行 "
                f"(レース {len(trainA_ids)}/{len(calib_ids)}/{len(test_ids)})")

    # 1段目ファンダ: オッズ/人気を入れずに学習
    X, feat = fundamental_features(df)
    y = df['is_win'].values
    clf = lgb.LGBMClassifier(objective='binary', n_estimators=500, learning_rate=0.03,
                             num_leaves=31, max_depth=5, min_child_samples=30,
                             subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
                             random_state=42, n_jobs=-1, verbosity=-1)
    clf.fit(X[A], y[A])
    df['f_raw'] = clf.predict_proba(X)[:, 1]
    df['f_norm'] = softmax_by_race(df.assign(_lf=np.log(np.clip(df['f_raw'], EPS, 1))), '_lf')

    # 2段目ブレンド: α,β を calib で推定
    alpha, beta = fit_blend(df[B])
    logger.info(f"ブレンド係数: α(自前)={alpha:.3f}  β(市場)={beta:.3f}")

    df['z'] = alpha * np.log(np.clip(df['f_norm'], EPS, 1)) + beta * np.log(np.clip(df['pi'], EPS, 1))
    df['c'] = softmax_by_race(df, 'z')

    # ── Go/No-Go: test での winner logloss 比較 ──
    test = df[T].copy()
    ll_market = winner_logloss(test, 'pi')      # 市場単独
    ll_fund = winner_logloss(test, 'f_norm')    # 自前単独
    ll_blend = winner_logloss(test, 'c')        # ブレンド
    print("\n" + "=" * 70)
    print("  Go/No-Go 判定 (test winner logloss・小さいほど良)")
    print("=" * 70)
    print(f"  市場単独(π)    : {ll_market:.4f}")
    print(f"  自前単独(f)    : {ll_fund:.4f}")
    print(f"  ブレンド(c)    : {ll_blend:.4f}")
    dlt = ll_market - ll_blend
    print(f"  ΔLL = 市場 - ブレンド = {dlt:+.4f}  → "
          f"{'✅ ブレンドが市場を上回る(増分情報あり=賭ける価値の前提クリア)' if dlt > 0 else '❌ 市場を上回れない(理論上どう賭けても負ける)'}")
    print("=" * 70)

    # ── オッズ帯別 バリューベット(ブレンド c で EV) ──
    test['ev'] = test['c'] * test['odds']
    winners, pays = {}, {}
    for rid, g in test.groupby('race_id'):
        w = g[g['rank_int'] == 1]
        if len(w) == 0:
            continue
        winners[rid] = str(w.iloc[0]['horse_number'])
        pv = pd.to_numeric(g['pay1'], errors='coerce').dropna()
        pays[rid] = float(pv.iloc[0]) if len(pv) else None

    print("\n  単勝バリュー(ブレンドEV>=1.1) オッズ帯別 回収率")
    print("-" * 70)
    print(f"  {'オッズ帯':>12} {'購入':>6} {'的中':>5} {'的中率':>7} {'回収率':>8}")
    bands = [(1, 5), (5, 10), (10, 20), (20, 50), (50, 9999)]
    for lo, hi in bands:
        sub = test[(test['ev'] >= 1.1) & (test['odds'] >= lo) & (test['odds'] < hi)]
        sub = sub[sub['race_id'].map(lambda r: pays.get(r) is not None)]
        n_b = len(sub)
        if n_b == 0:
            print(f"  {f'{lo}-{hi}':>12} {0:>6}")
            continue
        won = sub['horse_number'].astype(str) == sub['race_id'].map(winners)
        hit = int(won.sum())
        ret = float(sub.loc[won, 'race_id'].map(pays).sum())
        roi = ret / (n_b * 100) * 100
        print(f"  {f'{lo}-{hi}倍':>12} {n_b:>6} {hit:>5} {hit/n_b*100:>6.1f}% {roi:>7.1f}%")
    print("=" * 70)


if __name__ == '__main__':
    main()
