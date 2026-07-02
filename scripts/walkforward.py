#!/usr/bin/env python3
"""
@file    walkforward.py
@brief   ウォークフォワード(rolling-origin)検証 — 過学習/期間依存を排除した頑健性評価
@version 1.0.0  2026-06-28  新規作成 (Dicky1114)

なぜ必要か:
  1回の時系列分割だと「たまたまその未来が良/悪」だった可能性が残る。
  学習期間を伸ばしながら「次の未来ブロック」を順に検証(expanding window)し、
  ΔLL(市場ブレンド − 市場単独)と回収率が **複数期間で安定して＋か** を見る。
  一部期間でしか＋にならない=過学習/まぐれ=実戦では勝てない、と判定する。

各fold: train(過去) を ファンダ70% / ブレンド較正30% に分け、
        その先の未来ブロックを test として ΔLL と単勝バリュー回収率を測る。

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/walkforward.py
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
from scripts.market_blend import (
    fundamental_features, fit_blend, winner_logloss, softmax_by_race,
    GROUP_COLS, EPS,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

N_FOLDS = 5


def prep(df):
    df = df.copy()
    df['rank_int'] = pd.to_numeric(df['rank'], errors='coerce')
    df['is_win'] = (df['rank_int'] == 1).astype(int)
    df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
    df = df[df['odds'] > 0].copy()
    df['inv_odds'] = 1.0 / df['odds']
    df['pi'] = df.groupby('race_id')['inv_odds'].transform(lambda s: s / s.sum())
    return df


def run_fold(df, X, race_order, tr_end, te_end, clf_factory):
    """train=race_order[:tr_end], test=race_order[tr_end:te_end] で1fold評価。"""
    train_ids = set(race_order[:tr_end])
    test_ids = set(race_order[tr_end:te_end])
    # ファンダ70/較正30
    tr_list = race_order[:tr_end]
    cut = int(len(tr_list) * 0.7)
    A_ids = set(tr_list[:cut]); B_ids = set(tr_list[cut:])
    A = df['race_id'].isin(A_ids).values
    B = df['race_id'].isin(B_ids).values
    T = df['race_id'].isin(test_ids).values

    clf = clf_factory()
    clf.fit(X[A], df['is_win'].values[A])
    df = df.copy()
    df['f_raw'] = clf.predict_proba(X)[:, 1]
    df['f_norm'] = softmax_by_race(df.assign(_lf=np.log(np.clip(df['f_raw'], EPS, 1))), '_lf')

    alpha, beta = fit_blend(df[B])
    df['z'] = alpha * np.log(np.clip(df['f_norm'], EPS, 1)) + beta * np.log(np.clip(df['pi'], EPS, 1))
    df['c'] = softmax_by_race(df, 'z')

    test = df[T]
    ll_m = winner_logloss(test, 'pi')
    ll_b = winner_logloss(test, 'c')

    # 単勝バリュー(中オッズ帯 5-20倍, ブレンドEV>=1.1) 回収率
    test = test.copy()
    test['ev'] = test['c'] * test['odds']
    winners, pays = {}, {}
    for rid, g in test.groupby('race_id'):
        w = g[g['rank_int'] == 1]
        if len(w) == 0:
            continue
        winners[rid] = str(w.iloc[0]['horse_number'])
        pv = pd.to_numeric(g['pay1'], errors='coerce').dropna()
        pays[rid] = float(pv.iloc[0]) if len(pv) else None
    sub = test[(test['ev'] >= 1.1) & (test['odds'] >= 5) & (test['odds'] < 20)]
    sub = sub[sub['race_id'].map(lambda r: pays.get(r) is not None)]
    n_b = len(sub)
    if n_b:
        won = sub['horse_number'].astype(str) == sub['race_id'].map(winners)
        roi = float(sub.loc[won, 'race_id'].map(pays).sum()) / (n_b * 100) * 100
    else:
        roi = float('nan')

    return {'alpha': alpha, 'beta': beta, 'll_m': ll_m, 'll_b': ll_b,
            'dll': ll_m - ll_b, 'n_test': len(test_ids), 'n_bet': n_b, 'roi': roi}


def main():
    import lightgbm as lgb
    df = prep(load_data())
    X, feat = fundamental_features(df)
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races)

    def clf_factory():
        return lgb.LGBMClassifier(objective='binary', n_estimators=400, learning_rate=0.03,
                                  num_leaves=31, max_depth=5, min_child_samples=30,
                                  subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
                                  random_state=42, n_jobs=-1, verbosity=-1)

    # expanding window: 最初の40%を初期学習、残り60%を N_FOLDS 個の未来ブロックに分割
    start = int(n * 0.4)
    block = (n - start) // N_FOLDS
    print("\n" + "=" * 78)
    print("  ウォークフォワード検証 (expanding window・各foldは“未来”ブロック)")
    print("=" * 78)
    print(f"  {'fold':>4} {'学習レース':>9} {'検証レース':>9} {'α':>6} {'β':>6} "
          f"{'市場LL':>8} {'BlendLL':>8} {'ΔLL':>8} {'中ｵｯｽﾞ回収':>9}")
    print("-" * 78)
    rows = []
    for k in range(N_FOLDS):
        tr_end = start + k * block
        te_end = start + (k + 1) * block if k < N_FOLDS - 1 else n
        r = run_fold(df, X, races, tr_end, te_end, clf_factory)
        rows.append(r)
        roi_s = f"{r['roi']:.0f}%({r['n_bet']})" if r['n_bet'] else "—"
        print(f"  {k+1:>4} {tr_end:>9} {r['n_test']:>9} {r['alpha']:>6.2f} {r['beta']:>6.2f} "
              f"{r['ll_m']:>8.4f} {r['ll_b']:>8.4f} {r['dll']:>+8.4f} {roi_s:>9}")
    print("-" * 78)
    dlls = np.array([r['dll'] for r in rows])
    pos = (dlls > 0).sum()
    print(f"  ΔLL平均={dlls.mean():+.4f}  標準偏差={dlls.std():.4f}  "
          f"プラスのfold={pos}/{N_FOLDS}")
    verdict = ("✅ 複数期間で安定して市場に勝てる兆候" if pos >= N_FOLDS - 1 and dlls.mean() > 0
               else ("△ 一部期間のみ＝過学習/まぐれの疑い" if pos >= 2
                     else "❌ 市場に勝てない(増分情報なし)"))
    print(f"  判定: {verdict}")
    print("=" * 78)


if __name__ == '__main__':
    main()
