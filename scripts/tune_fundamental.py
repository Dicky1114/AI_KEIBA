#!/usr/bin/env python3
"""
@file    tune_fundamental.py
@brief   1段目LightGBMのハイパラを「ウォークフォワードΔLL」で探索(過学習耐性つき調整)
@version 1.0.0  2026-06-28  新規作成 (Dicky1114)

注意: バックテストが良くなるまで弄るのは過学習。よって
  - 前半foldで良かった設定が後半foldでも＋か(汎化)を見る。
  - 採点は単一分割でなくウォークフォワードΔLLの平均/安定性。

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/tune_fundamental.py
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
from scripts.science_menu import prep

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

N_FOLDS = 5

# 探索する設定(過学習を抑える方向に幅を取る)
CONFIGS = {
    'baseline':     dict(num_leaves=31, max_depth=5, min_child_samples=30, learning_rate=0.03, n_estimators=400, reg_lambda=5.0),
    '浅い+強正則':   dict(num_leaves=15, max_depth=4, min_child_samples=60, learning_rate=0.03, n_estimators=500, reg_lambda=10.0),
    '極浅+最強正則': dict(num_leaves=8,  max_depth=3, min_child_samples=100, learning_rate=0.02, n_estimators=600, reg_lambda=20.0),
    '深い(過学習側)': dict(num_leaves=63, max_depth=8, min_child_samples=10, learning_rate=0.05, n_estimators=400, reg_lambda=1.0),
    '低LR+多本数':   dict(num_leaves=31, max_depth=5, min_child_samples=40, learning_rate=0.015, n_estimators=900, reg_lambda=8.0),
}


def walkforward_dll(df, Xv, y, params):
    import lightgbm as lgb
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races)
    start = int(n * 0.4)
    block = (n - start) // N_FOLDS
    dlls = []
    for k in range(N_FOLDS):
        tr_end = start + k * block
        te_end = start + (k + 1) * block if k < N_FOLDS - 1 else n
        tr_list = races[:tr_end]
        cut = int(len(tr_list) * 0.7)
        A = df['race_id'].isin(set(tr_list[:cut])).values
        B = df['race_id'].isin(set(tr_list[cut:])).values
        T = df['race_id'].isin(set(races[tr_end:te_end])).values
        m = lgb.LGBMClassifier(objective='binary', subsample=0.8, colsample_bytree=0.8,
                               random_state=42, n_jobs=-1, verbosity=-1, **params)
        m.fit(Xv[A], y[A])
        d = df.copy()
        d['f_raw'] = m.predict_proba(Xv)[:, 1]
        d['f_norm'] = softmax_by_race(d.assign(_lf=np.log(np.clip(d['f_raw'], EPS, 1))), '_lf')
        a, b = fit_blend(d[B])
        d['z'] = a * np.log(np.clip(d['f_norm'], EPS, 1)) + b * np.log(np.clip(d['pi'], EPS, 1))
        d['c'] = softmax_by_race(d, 'z')
        t = d[T]
        dlls.append(winner_logloss(t, 'pi') - winner_logloss(t, 'c'))
    return np.array(dlls)


def main():
    df = prep(load_data())
    X, feat = fundamental_features(df)
    Xv = X.values.astype('float32')
    y = df['is_win'].values
    logger.info(f"データ {len(df)}行/{df['race_id'].nunique()}レース 特徴量{len(feat)}")

    print("\n" + "=" * 92)
    print("  ハイパラ探索 (採点=ウォークフォワードΔLL・前半foldと後半foldの両立を見る)")
    print("=" * 92)
    print(f"  {'設定':<16}{'ΔLL平均':>9}{'σ':>8}{'＋fold':>7}  前半2fold / 後半3fold  fold別")
    print("-" * 92)
    for name, params in CONFIGS.items():
        d = walkforward_dll(df, Xv, y, params)
        first = d[:2].mean(); last = d[2:].mean()
        pos = int((d > 0).sum())
        mark = '✅' if (pos >= 4 and d.mean() > 0) else ('△' if pos >= 3 else '❌')
        print(f"  {name:<16}{d.mean():>+9.4f}{d.std():>8.4f}{pos:>5}/5  "
              f"{first:>+7.4f} / {last:>+7.4f}  {mark}  [{' '.join(f'{x:+.3f}' for x in d)}]")
    print("=" * 92)
    print("  ※ 前半で良く後半で崩れる=過学習。両方＋で安定が本物。")


if __name__ == '__main__':
    main()
