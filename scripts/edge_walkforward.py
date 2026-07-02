#!/usr/bin/env python3
"""
@file    edge_walkforward.py
@brief   edge_analysis で見つけた絞り込みルールが「時間を変えても再現するか」を検証
@version 1.0.0  2026-06-30  (Dicky1114)

なぜ:
  単一splitで回収率>100%のセルは、多数セルを試した上澄み=偶然の上振れかもしれない。
  本物のエッジなら、学習区間をずらした複数の未来foldでも >100% が安定するはず。
  各foldで past→train+calib / next-block→test とし、候補ルールの回収率を出す。

候補ルール(edge_analysis の発見):
  R1 単勝: モデル1位 & オッズ3-5倍 & 較正勝率25-35%
  R2 単勝: モデル1位 & オッズ3-8倍 & 較正勝率>=25% (R1を少し広げ頑健性確認)
  R3 複勝: モデル2位評価 & 単勝オッズ5-8倍
  比較用 B  単勝: モデル1位 全部(絞り無し)

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/edge_walkforward.py
"""
import os, sys, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import django  # noqa
django.setup()

from scripts.run_roi_analysis import load_data
from scripts.value_betting import build_xy

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
UNIT = 100
N_FOLDS = 5


def fit_predict_block(df, X, y, train_mask, calib_mask, test_mask):
    import lightgbm as lgb
    from sklearn.isotonic import IsotonicRegression
    clf = lgb.LGBMClassifier(
        objective='binary', n_estimators=600, learning_rate=0.03,
        num_leaves=31, max_depth=5, min_child_samples=30,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
        random_state=42, n_jobs=-1, verbosity=-1,
    )
    clf.fit(X[train_mask], y[train_mask], eval_set=[(X[calib_mask], y[calib_mask])],
            callbacks=[lgb.early_stopping(50, verbose=False)])
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(clf.predict_proba(X[calib_mask])[:, 1], y[calib_mask].values)
    p = iso.transform(clf.predict_proba(X[test_mask])[:, 1])

    t = df[test_mask].copy()
    t['odds'] = pd.to_numeric(t['odds'], errors='coerce')
    t['p_hat'] = p
    t = t[t['odds'] > 0].dropna(subset=['odds'])
    t['p_norm'] = t.groupby('race_id')['p_hat'].transform(lambda s: s / s.sum() if s.sum() > 0 else s)
    t['rank_int'] = pd.to_numeric(t['rank'], errors='coerce')
    t['model_rank'] = t.groupby('race_id')['p_norm'].rank(ascending=False, method='first')
    for c in ['pay1', 'pay123_1', 'pay123_2', 'pay123_3']:
        if c in t.columns:
            t[c] = pd.to_numeric(t[c].astype(str).str.replace(',', ''), errors='coerce')
    return t


def ret_win(g):
    return np.where(g['rank_int'] == 1, g['pay1'].fillna(0), 0.0)


def ret_place(g):
    r = g['rank_int']
    out = np.select(
        [r == 1, r == 2, r == 3],
        [g['pay123_1'].fillna(0), g['pay123_2'].fillna(0), g['pay123_3'].fillna(0)],
        default=0.0)
    return out


RULES = {
    'B  単勝 model1位 全部':
        lambda t: (t[t['model_rank'] == 1], 'win'),
    'R1 単勝 1位×3-5倍×25-35%':
        lambda t: (t[(t['model_rank'] == 1) & (t['odds'] >= 3) & (t['odds'] < 5)
                     & (t['p_norm'] >= .25) & (t['p_norm'] < .35)], 'win'),
    'R2 単勝 1位×3-8倍×p>=25%':
        lambda t: (t[(t['model_rank'] == 1) & (t['odds'] >= 3) & (t['odds'] < 8)
                     & (t['p_norm'] >= .25)], 'win'),
    'R3 複勝 model2位×5-8倍':
        lambda t: (t[(t['model_rank'] == 2) & (t['odds'] >= 5) & (t['odds'] < 8)], 'place'),
}


def main():
    df = load_data()
    X, y, _ = build_xy(df)
    races = df[['today_race_date', 'race_id']].drop_duplicates().sort_values(['today_race_date', 'race_id'])
    rid_order = races['race_id'].tolist()
    n = len(rid_order)
    # 前半50%を最初の学習に固定し、残り50%をN_FOLDSブロックに分割して順に未来テスト
    start = n // 2
    block = (n - start) // N_FOLDS
    logger.info(f"全{n}レース: 初期学習={start}, 1fold≈{block}レース, {N_FOLDS}fold")

    agg = {k: {'n': 0, 'hit': 0, 'bet': 0.0, 'ret': 0.0, 'rois': []} for k in RULES}
    for f in range(N_FOLDS):
        te_lo = start + f * block
        te_hi = start + (f + 1) * block if f < N_FOLDS - 1 else n
        test_ids = set(rid_order[te_lo:te_hi])
        # 学習区間 = テスト直前まで。うち後ろ15%を較正に
        past = rid_order[:te_lo]
        n_ca = int(len(past) * 0.15)
        calib_ids = set(past[len(past) - n_ca:])
        train_ids = set(past[:len(past) - n_ca])
        tr = df['race_id'].isin(train_ids).values
        ca = df['race_id'].isin(calib_ids).values
        te = df['race_id'].isin(test_ids).values
        t = fit_predict_block(df, X, y, tr, ca, te)

        line = []
        for name, rule in RULES.items():
            sub, kind = rule(t)
            if len(sub) == 0:
                line.append(f"{name.split()[0]}:0")
                continue
            r = ret_win(sub) if kind == 'win' else ret_place(sub)
            nb = len(sub); hit = int((r > 0).sum()); ret = float(r.sum()); bet = nb * UNIT
            roi = ret / bet * 100
            agg[name]['n'] += nb; agg[name]['hit'] += hit
            agg[name]['bet'] += bet; agg[name]['ret'] += ret; agg[name]['rois'].append(roi)
            line.append(f"{name.split()[0]}:{roi:.0f}%(n{nb})")
        logger.info(f"fold{f+1} test={len(test_ids)}R  " + "  ".join(line))

    print("\n" + "=" * 82)
    print("  ウォークフォワード集計(5fold通算) — 絞り込みルールの再現性")
    print("=" * 82)
    print(f"  {'ルール':<26} {'購入':>5} {'的中':>5} {'的中率':>7} {'通算回収率':>9} {'fold別ROI(平均±σ)':>20}")
    print("-" * 82)
    for name, a in agg.items():
        if a['n'] == 0:
            print(f"  {name:<26} {'0':>5}")
            continue
        roi = a['ret'] / a['bet'] * 100
        rois = np.array(a['rois'])
        print(f"  {name:<26} {a['n']:>5} {a['hit']:>5} {a['hit']/a['n']*100:>6.1f}% "
              f"{roi:>8.1f}%  {rois.mean():>7.0f}±{rois.std():>3.0f}% (n{len(rois)}fold)")
    print("=" * 82)
    print("  判定: 通算>100% かつ fold別が安定して(σが小さく)>100% なら本物候補。")
    print("        σが平均と同程度・赤字foldありなら『偶然の上振れ』。")


if __name__ == '__main__':
    main()
