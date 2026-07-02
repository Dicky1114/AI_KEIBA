#!/usr/bin/env python3
"""
@file    value_betting.py
@brief   較正済み勝率モデルによるバリューベット(+EVのみ購入)+ケリー複利バックテスト
@version 2.0.0  2026-06-28  ランカーsoftmax(未較正)を二値分類+isotonic較正に置換 (Dicky1114)

考え方:
  控除率(約20%)に勝つには「全部買う」では不可能。較正済みの勝率 p_hat を出し、
  市場オッズと比べて 期待値 EV = p_hat × odds > 1 の馬だけ買う。
  賭け金は分数ケリー f* = (b·p − q)/b (b=odds−1) で複利運用する。

なぜ二値分類か:
  ランカー(LambdaRank)は順位最適化で確率の絶対値を出さない。
  EV計算には較正された勝率が要るので、LightGBM二値分類 + CalibratedClassifierCV(isotonic)。
  予測勝率はレース内で正規化(合計=1)してから EV を計算する。

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/value_betting.py
"""

import os
import sys
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import numpy as np
import pandas as pd

from scripts.run_roi_analysis import load_data  # CSVローダを再利用

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BET_UNIT = 100
RESULT_COLS = ['rank', 'race_time', 'corner_order', 'last_3f', 'margin',
               'positions', 'positions_tie',
               'pay1', 'pay1_tie', 'pay123_1', 'pay123_2', 'pay123_3',
               'pay12_21', 'pay12_12', 'pay123_321', 'pay123_123']
GROUP_COLS = ['today_race_date', 'race_id']


def build_xy(df: pd.DataFrame):
    """特徴量X(数値化) と 勝ち=1 のラベルyを作る。"""
    df = df.copy()
    df['rank_int'] = pd.to_numeric(df['rank'], errors='coerce')
    df['is_win'] = (df['rank_int'] == 1).astype(int)

    exclude = set(RESULT_COLS + GROUP_COLS + ['horse_number', 'rank_int', 'is_win', 'id'])
    feat = [c for c in df.columns if c not in exclude]
    X = df[feat].copy()
    for c in X.columns:
        if X[c].dtype == 'object':
            X[c] = X[c].astype('category').cat.codes  # ラベルエンコード
        else:
            X[c] = pd.to_numeric(X[c], errors='coerce')
    X = X.fillna(-1).astype('float32')
    return X, df['is_win'].astype(int), feat


def time_split(df: pd.DataFrame, test_frac=0.2, calib_frac=0.15):
    """レース単位の時系列split: 学習 / 較正 / テスト。"""
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)
    n = len(races)
    n_test = int(n * test_frac)
    n_calib = int(n * calib_frac)
    test_ids = set(races.iloc[n - n_test:]['race_id'])
    calib_ids = set(races.iloc[n - n_test - n_calib:n - n_test]['race_id'])
    train_ids = set(races.iloc[:n - n_test - n_calib]['race_id'])
    return train_ids, calib_ids, test_ids


def main():
    import lightgbm as lgb
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import roc_auc_score, log_loss

    df = load_data()
    X, y, feat = build_xy(df)
    train_ids, calib_ids, test_ids = time_split(df)
    tr = df['race_id'].isin(train_ids).values
    ca = df['race_id'].isin(calib_ids).values
    te = df['race_id'].isin(test_ids).values
    logger.info(f"学習={tr.sum()}行 較正={ca.sum()}行 テスト={te.sum()}行 "
                f"(レース {len(train_ids)}/{len(calib_ids)}/{len(test_ids)})")

    clf = lgb.LGBMClassifier(
        objective='binary', n_estimators=600, learning_rate=0.03,
        num_leaves=31, max_depth=5, min_child_samples=30,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
        random_state=42, n_jobs=-1, verbosity=-1,
    )
    clf.fit(X[tr], y[tr], eval_set=[(X[ca], y[ca])],
            callbacks=[lgb.early_stopping(50, verbose=False)])

    # 較正(isotonic): 較正セットの生確率→実勝率 へ写像
    raw_ca = clf.predict_proba(X[ca])[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(raw_ca, y[ca].values)

    raw_te = clf.predict_proba(X[te])[:, 1]
    p_te = iso.transform(raw_te)
    try:
        auc = roc_auc_score(y[te], p_te)
        ll = log_loss(y[te], np.clip(p_te, 1e-6, 1 - 1e-6))
        logger.info(f"テスト AUC={auc:.4f} logloss={ll:.4f}")
    except Exception:
        pass

    # テストDF構築
    t = df[te].copy()
    t['odds'] = pd.to_numeric(t['odds'], errors='coerce')
    t['p_hat'] = p_te
    t = t.dropna(subset=['odds'])
    t = t[t['odds'] > 0]
    # レース内で勝率を正規化(合計=1)
    t['p_norm'] = t.groupby('race_id')['p_hat'].transform(lambda s: s / s.sum() if s.sum() > 0 else s)
    t['ev'] = t['p_norm'] * t['odds']
    t['rank_int'] = pd.to_numeric(t['rank'], errors='coerce')

    # 決済情報
    winners, pays = {}, {}
    for rid, g in t.groupby('race_id'):
        w = g[g['rank_int'] == 1]
        if len(w) == 0:
            continue
        winners[rid] = str(w.iloc[0]['horse_number'])
        pv = pd.to_numeric(g['pay1'], errors='coerce').dropna()
        pays[rid] = float(pv.iloc[0]) if len(pv) else None

    print("\n" + "=" * 78)
    print("  バリューベット(単勝・較正済み勝率・EV>=閾値のみ購入) — 定額100円")
    print("=" * 78)
    print(f"  {'EV閾値':>6} {'購入数':>6} {'的中':>5} {'的中率':>7} {'平均オッズ':>9} {'賭金':>9} {'回収':>10} {'回収率':>8}")
    print("-" * 78)
    best = None
    for th in [1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.5]:
        sub = t[t['ev'] >= th]
        sub = sub[sub['race_id'].map(lambda r: pays.get(r) is not None)]
        n = len(sub)
        if n == 0:
            print(f"  {th:>6.2f} {0:>6}")
            continue
        won = sub['horse_number'].astype(str) == sub['race_id'].map(winners)
        hit = int(won.sum())
        ret = float(sub.loc[won, 'race_id'].map(pays).sum())
        bet = n * BET_UNIT
        roi = ret / bet * 100
        print(f"  {th:>6.2f} {n:>6} {hit:>5} {hit/n*100:>6.1f}% {sub['odds'].mean():>9.1f} "
              f"{bet:>9,} {int(ret):>10,} {roi:>7.1f}%")
        if n >= 20 and (best is None or roi > best[1]):
            best = (th, roi)
    print("=" * 78)

    # ケリー複利(最良閾値)
    th = best[0] if best else 1.1
    bankroll = bankroll0 = 100000.0
    peak = bankroll0
    max_dd = 0.0
    nb = hb = 0
    for rid, g in t.sort_values(['today_race_date', 'race_id']).groupby('race_id', sort=False):
        if pays.get(rid) is None:
            continue
        for _, r in g.iterrows():
            if r['ev'] < th:
                continue
            p = float(r['p_norm']); b = float(r['odds']) - 1.0
            if b <= 0:
                continue
            f = (b * p - (1 - p)) / b
            if f <= 0:
                continue
            stake = bankroll * min(f * 0.25, 0.05)
            if stake < 100:
                continue
            nb += 1
            if str(r['horse_number']) == winners.get(rid):
                bankroll += stake * (float(r['odds']) - 1.0); hb += 1
            else:
                bankroll -= stake
            peak = max(peak, bankroll)
            max_dd = max(max_dd, (peak - bankroll) / peak)
    print(f"  ケリー複利 (EV>={th}, 初期10万, 1/4ケリー, 上限5%): "
          f"ベット{nb} 的中{hb} 最終{int(bankroll):,}円 (×{bankroll/bankroll0:.2f}) 最大DD={max_dd*100:.1f}%")
    print("=" * 78)


if __name__ == '__main__':
    main()
