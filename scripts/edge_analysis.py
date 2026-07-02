#!/usr/bin/env python3
"""
@file    edge_analysis.py
@brief   「どのスコア(較正勝率)・オッズ帯が当たって外れるか」を分解し、回収率>100%の部分集合を探す
@version 1.0.0  2026-06-30  (Dicky1114)

考え方:
  全部買うと控除率に負ける。EV>1 で絞ると大穴に偏って負ける(検証済)。
  → モデルの実力(AUC0.84)が出る「本命寄り・高確信」帯を直接探す。
  単勝・複勝それぞれで、テスト区間(未来)の予測を
    ① 確信度(較正勝率 p_hat)帯
    ② オッズ帯
    ③ 確信度×オッズ のクロス
  に分けて 購入数/的中率/回収率 を出し、回収率>100%のセルを特定する。

  ※「絞る」= ある帯だけ買えば回収率が改善するかを見るためのもの。
    サンプルが小さいセルはノイズ(注記する)。

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/edge_analysis.py
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
from scripts.value_betting import build_xy, time_split

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
UNIT = 100


def build_test_frame() -> pd.DataFrame:
    """較正済み勝率 p_hat を付けたテスト区間DFを返す。複勝判定用に rank も保持。"""
    import lightgbm as lgb
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import roc_auc_score, log_loss

    df = load_data()
    X, y, feat = build_xy(df)
    tr_ids, ca_ids, te_ids = time_split(df)
    tr = df['race_id'].isin(tr_ids).values
    ca = df['race_id'].isin(ca_ids).values
    te = df['race_id'].isin(te_ids).values
    logger.info(f"学習={tr.sum()} 較正={ca.sum()} テスト={te.sum()} "
                f"(レース {len(tr_ids)}/{len(ca_ids)}/{len(te_ids)})")

    clf = lgb.LGBMClassifier(
        objective='binary', n_estimators=600, learning_rate=0.03,
        num_leaves=31, max_depth=5, min_child_samples=30,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
        random_state=42, n_jobs=-1, verbosity=-1,
    )
    clf.fit(X[tr], y[tr], eval_set=[(X[ca], y[ca])],
            callbacks=[lgb.early_stopping(50, verbose=False)])
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(clf.predict_proba(X[ca])[:, 1], y[ca].values)
    p_te = iso.transform(clf.predict_proba(X[te])[:, 1])
    logger.info(f"テスト AUC={roc_auc_score(y[te], p_te):.4f} "
                f"logloss={log_loss(y[te], np.clip(p_te, 1e-6, 1-1e-6)):.4f}")

    t = df[te].copy()
    t['odds'] = pd.to_numeric(t['odds'], errors='coerce')
    t['popularity'] = pd.to_numeric(t['popularity'], errors='coerce')
    t['p_hat'] = p_te
    t = t[t['odds'] > 0].dropna(subset=['odds'])
    t['p_norm'] = t.groupby('race_id')['p_hat'].transform(lambda s: s / s.sum() if s.sum() > 0 else s)
    t['ev'] = t['p_norm'] * t['odds']
    t['rank_int'] = pd.to_numeric(t['rank'], errors='coerce')
    # レース内のモデル順位(1=最有力)
    t['model_rank'] = t.groupby('race_id')['p_norm'].rank(ascending=False, method='first')
    for c in ['pay1', 'pay123_1', 'pay123_2', 'pay123_3']:
        if c in t.columns:
            t[c] = pd.to_numeric(t[c].astype(str).str.replace(',', ''), errors='coerce')
    return t


def settle_win(row):
    """単勝: 1着なら pay1, 外れ0。"""
    return float(row['pay1']) if row['rank_int'] == 1 and pd.notna(row['pay1']) else 0.0


def settle_place(row):
    """複勝: 3着以内なら該当pay、外れ0。"""
    r = row['rank_int']
    if r == 1:
        v = row.get('pay123_1')
    elif r == 2:
        v = row.get('pay123_2')
    elif r == 3:
        v = row.get('pay123_3')
    else:
        return 0.0
    return float(v) if pd.notna(v) else 0.0


def roi_table(bets: pd.DataFrame, payout_col: str, by: str, bins, labels, title: str):
    """bets を by 列の bins で区切り、各帯の 購入数/的中/的中率/回収率 を出す。"""
    b = bets.copy()
    b['bucket'] = pd.cut(b[by], bins=bins, labels=labels, include_lowest=True, right=False)
    print(f"\n  ── {title} ──")
    print(f"  {'帯':>14} {'購入':>6} {'的中':>5} {'的中率':>7} {'平均ODDS':>8} {'回収率':>8}  {'判定':<6}")
    print("  " + "-" * 70)
    rows = []
    for lab, g in b.groupby('bucket', observed=True):
        n = len(g)
        if n == 0:
            continue
        hit = int((g[payout_col] > 0).sum())
        ret = g[payout_col].sum()
        roi = ret / (n * UNIT) * 100
        note = 'ノイズ' if n < 30 else ('★勝' if roi >= 100 else '')
        print(f"  {str(lab):>14} {n:>6} {hit:>5} {hit/n*100:>6.1f}% "
              f"{g['odds'].mean():>8.1f} {roi:>7.1f}%  {note:<6}")
        rows.append((lab, n, hit, roi))
    return rows


def main():
    t = build_test_frame()

    # ===== 単勝: モデル1位の馬だけを母集団にする =====
    win = t[t['model_rank'] == 1].copy()
    win['ret'] = win.apply(settle_win, axis=1)
    n = len(win)
    base_roi = win['ret'].sum() / (n * UNIT) * 100
    print("\n" + "=" * 74)
    print(f"  単勝・モデル1位 全{n}レース  回収率 {base_roi:.1f}% (絞り無しの基準)")
    print("=" * 74)
    roi_table(win, 'ret', 'p_norm',
              bins=[0, .15, .25, .35, .50, 1.01],
              labels=['~15%', '15-25%', '25-35%', '35-50%', '50%+'],
              title='確信度(較正勝率)帯別')
    roi_table(win, 'ret', 'odds',
              bins=[0, 2, 3, 5, 8, 15, 1e9],
              labels=['~2.0', '2-3', '3-5', '5-8', '8-15', '15+'],
              title='オッズ帯別')
    roi_table(win, 'ret', 'popularity',
              bins=[0, 1.5, 2.5, 3.5, 5.5, 99],
              labels=['1番人気', '2番人気', '3番人気', '4-5番', '6番以下'],
              title='人気別')

    # クロス: オッズ帯 × 確信度
    print("\n  ── クロス: オッズ帯 × 確信度(回収率%/購入数) ──")
    win['ob'] = pd.cut(win['odds'], [0, 3, 5, 8, 1e9], labels=['~3', '3-5', '5-8', '8+'], right=False)
    win['cb'] = pd.cut(win['p_norm'], [0, .25, .35, 1.01], labels=['~25%', '25-35%', '35%+'], right=False)
    piv_roi = win.groupby(['ob', 'cb'], observed=True).apply(
        lambda g: g['ret'].sum() / (len(g) * UNIT) * 100).unstack()
    piv_n = win.groupby(['ob', 'cb'], observed=True).size().unstack()
    print("  回収率%:\n", piv_roi.round(0).to_string())
    print("  購入数:\n", piv_n.to_string())

    # ===== 複勝: モデル1位/2位を母集団 (的中多くノイズ少ない) =====
    for mr in [1, 2]:
        pl = t[t['model_rank'] == mr].copy()
        pl['ret'] = pl.apply(settle_place, axis=1)
        n = len(pl)
        base = pl['ret'].sum() / (n * UNIT) * 100
        print("\n" + "=" * 74)
        print(f"  複勝・モデル{mr}位 全{n}レース  回収率 {base:.1f}% (絞り無し基準)")
        print("=" * 74)
        roi_table(pl, 'ret', 'odds',
                  bins=[0, 2, 3, 5, 8, 15, 1e9],
                  labels=['~2.0', '2-3', '3-5', '5-8', '8-15', '15+'],
                  title='単勝オッズ帯別(複勝)')
        roi_table(pl, 'ret', 'p_norm',
                  bins=[0, .15, .25, .35, .50, 1.01],
                  labels=['~15%', '15-25%', '25-35%', '35-50%', '50%+'],
                  title='確信度帯別(複勝)')


if __name__ == '__main__':
    main()
