#!/usr/bin/env python3
"""
@file    science_menu.py
@brief   科学メニュー: モデル比較(LGB/Logistic/アンサンブル) + 特徴グループ アブレーション
@version 1.0.0  2026-06-28  新規作成 (Dicky1114)

全構成を共通の「ウォークフォワードΔLL(市場ブレンド − 市場単独)」で採点する。
ΔLL>0 が複数foldで安定 = 市場に勝てる兆候。1回の分割の良さは過学習として割り引く。

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/science_menu.py
"""

import os
import sys
import logging
import warnings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

from scripts.run_roi_analysis import load_data
from scripts.market_blend import fundamental_features, fit_blend, winner_logloss, softmax_by_race, GROUP_COLS, EPS

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

N_FOLDS = 5
GROUPS = {
    'speed': ['prev_speed', 'avg_speed3', 'best_speed'],
    'jockey': ['j_runs_prior', 'j_win_rate_prior', 'j_place_rate_prior'],
    'history': ['prev_rank', 'prev_popularity', 'prev_last3f', 'prev_odds', 'days_since_last',
                'avg_rank3', 'best_rank_prior', 'n_runs_prior', 'win_rate_prior', 'place_rate_prior'],
}


def prep(df):
    df = df.copy()
    df['rank_int'] = pd.to_numeric(df['rank'], errors='coerce')
    df['is_win'] = (df['rank_int'] == 1).astype(int)
    df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
    df = df[df['odds'] > 0].copy()
    df['inv_odds'] = 1.0 / df['odds']
    df['pi'] = df.groupby('race_id')['inv_odds'].transform(lambda s: s / s.sum())
    return df


def make_predictor(kind):
    """kind: 'lgb' | 'logit' | 'ensemble' → fit(Xtr,ytr)→predict(X)→f_raw を返すクロージャ。"""
    import lightgbm as lgb
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    def predict(Xtr, ytr, Xall):
        out = []
        if kind in ('lgb', 'ensemble'):
            m = lgb.LGBMClassifier(objective='binary', n_estimators=400, learning_rate=0.03,
                                   num_leaves=31, max_depth=5, min_child_samples=30, subsample=0.8,
                                   colsample_bytree=0.8, reg_lambda=5.0, random_state=42, n_jobs=-1, verbosity=-1)
            m.fit(Xtr, ytr)
            out.append(m.predict_proba(Xall)[:, 1])
        if kind in ('logit', 'ensemble'):
            sc = StandardScaler()
            Xtr_s = sc.fit_transform(np.nan_to_num(Xtr, nan=-1))
            Xall_s = sc.transform(np.nan_to_num(Xall, nan=-1))
            lr = LogisticRegression(max_iter=1000, C=0.5)
            lr.fit(Xtr_s, ytr)
            out.append(lr.predict_proba(Xall_s)[:, 1])
        return np.mean(out, axis=0)
    return predict


def walkforward_dll(df, X, predict_fn):
    """expanding window で各foldのΔLL(市場−ブレンド)を返す。"""
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races)
    start = int(n * 0.4)
    block = (n - start) // N_FOLDS
    Xv = X.values.astype('float32')
    y = df['is_win'].values
    dlls = []
    for k in range(N_FOLDS):
        tr_end = start + k * block
        te_end = start + (k + 1) * block if k < N_FOLDS - 1 else n
        tr_list = races[:tr_end]
        cut = int(len(tr_list) * 0.7)
        A = df['race_id'].isin(set(tr_list[:cut])).values
        B = df['race_id'].isin(set(tr_list[cut:])).values
        T = df['race_id'].isin(set(races[tr_end:te_end])).values

        f_raw = predict_fn(Xv[A], y[A], Xv)
        d = df.copy()
        d['f_raw'] = f_raw
        d['f_norm'] = softmax_by_race(d.assign(_lf=np.log(np.clip(d['f_raw'], EPS, 1))), '_lf')
        a, b = fit_blend(d[B])
        d['z'] = a * np.log(np.clip(d['f_norm'], EPS, 1)) + b * np.log(np.clip(d['pi'], EPS, 1))
        d['c'] = softmax_by_race(d, 'z')
        t = d[T]
        dlls.append(winner_logloss(t, 'pi') - winner_logloss(t, 'c'))
    return np.array(dlls)


def report(name, dlls):
    pos = int((dlls > 0).sum())
    mark = '✅' if (pos >= N_FOLDS - 1 and dlls.mean() > 0) else ('△' if pos >= 3 else '❌')
    print(f"  {name:<28} ΔLL平均={dlls.mean():+.4f} σ={dlls.std():.4f} "
          f"＋fold={pos}/{N_FOLDS} {mark}  [{' '.join(f'{x:+.3f}' for x in dlls)}]")


def main():
    df = prep(load_data())
    X_full, feat = fundamental_features(df)
    logger.info(f"データ {len(df)}行 / {df['race_id'].nunique()}レース / 特徴量{len(feat)}")

    print("\n" + "=" * 96)
    print("  科学メニュー: ウォークフォワードΔLL (市場ブレンド − 市場単独 / ＋=市場に勝てる増分)")
    print("=" * 96)
    print("  [モデル比較] 全特徴")
    for kind, label in [('lgb', 'LightGBM'), ('logit', 'Logistic回帰'), ('ensemble', 'アンサンブル(LGB+Logit)')]:
        report(label, walkforward_dll(df, X_full, make_predictor(kind)))

    print("\n  [特徴アブレーション] LightGBMから各グループを除外")
    base = walkforward_dll(df, X_full, make_predictor('lgb'))
    report('全特徴(基準)', base)
    for gname, cols in GROUPS.items():
        drop = [c for c in cols if c in X_full.columns]
        Xa = X_full.drop(columns=drop)
        report(f'−{gname}を除外', walkforward_dll(df, Xa, make_predictor('lgb')))
    print("=" * 96)
    print("  ※ ✅=複数foldで安定して＋(勝てる兆候) / △=一部のみ(過学習疑い) / ❌=増分情報なし")


if __name__ == '__main__':
    main()
