#!/usr/bin/env python3
"""
@file    run_roi_analysis.py
@brief   既存CSV + ResultDataを使ってML学習 → ROI回収率シミュレーション
@version 1.0.0  2026-03-31  新規作成 (Dicky1114)

使用方法:
    cd /home/dickey/デスクトップ/01_開発/02_dickey/03_keiba
    source venv/bin/activate
    python scripts/run_roi_analysis.py
"""

import os
import sys
import logging
import json
import numpy as np
import pandas as pd
from itertools import permutations, combinations

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ─── データ準備 ───────────────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    """build_dataset_pandas.py が出力した学習CSV(払戻込み)を読み込む。

    WHY: 旧版は未コミットの train_data_enhanced.csv + 壊れたビュー依存だった。
         build_dataset_pandas.py は payouts を内包するため再JOIN不要。
    """
    import glob
    csv_dir = os.path.join(BASE_DIR, 'media', 'csv_export')
    candidates = sorted(glob.glob(os.path.join(csv_dir, 'train_data_pandas_*.csv')),
                        key=os.path.getmtime, reverse=True)
    if not candidates:
        # フォールバック: 旧固定名
        legacy = os.path.join(csv_dir, 'train_data_enhanced.csv')
        if os.path.exists(legacy):
            candidates = [legacy]
        else:
            raise FileNotFoundError("train_data_pandas_*.csv が見つかりません。先に build_dataset_pandas.py を実行してください。")
    csv_path = candidates[0]
    logger.info(f"Loading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    df['race_id'] = df['race_id'].astype(str)
    df['horse_number'] = df['horse_number'].astype(str)

    # 払戻列を数値化(カンマ除去)
    for col in ['pay1', 'pay123_1', 'pay123_2', 'pay123_3', 'pay12_21', 'pay12_12',
                'pay123_321', 'pay123_123']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

    logger.info(f"Dataset: {len(df)} rows, {df['race_id'].nunique()} races")
    return df


# ─── ML学習 ──────────────────────────────────────────────────────────────────
def train_model(df: pd.DataFrame):
    """LightGBM LambdaRank でモデルを学習する。"""
    import lightgbm as lgb
    from sklearn.model_selection import GroupShuffleSplit

    RESULT_COLS = [
        'rank', 'race_time', 'corner_order', 'last_3f', 'margin', 'positions', 'positions_tie',
        'pay1', 'pay1_tie', 'pay123_1', 'pay123_2', 'pay123_3',
        'pay123_12_1', 'pay123_12_2', 'pay123_12_3', 'pay123_12_4_tie', 'pay123_12_5_tie',
        'pay12_21', 'pay12_21_tie', 'pay12_12', 'pay12_12_tie',
        'pay123_321', 'pay123_321_tie', 'pay123_123', 'pay123_123_tie',
    ]
    GROUP_COLS = ['today_race_date', 'race_id']
    TARGET_COL = 'rank_relation'
    DROP_FEATURES = ['frame_number', 'body_weight', 'body_weight_diff', 'inv_popularity', 'odds_rank']

    # ターゲット生成
    df['rank_int'] = pd.to_numeric(df['rank'], errors='coerce')
    df[TARGET_COL] = df['rank_int'].apply(
        lambda x: 30 if x == 1 else (20 if x == 2 else (10 if x == 3 else 0))
    )

    exclude = set(RESULT_COLS + GROUP_COLS + [TARGET_COL, 'id', 'race_id', 'horse_number', 'rank_int'] + DROP_FEATURES)
    feature_cols = [c for c in df.columns if c not in exclude]

    X = df[feature_cols].copy()
    y = df[TARGET_COL].copy()

    # カテゴリ変数処理
    cat_cols = []
    for col in X.columns:
        if X[col].dtype == 'object':
            X[col] = X[col].astype('category')
            cat_cols.append(col)
        elif X[col].nunique() <= 10 and col not in ['age', 'count', 'race_no', 'jockey_count']:
            X[col] = X[col].astype('category')
            cat_cols.append(col)
        else:
            X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0).astype('float32')

    y = y.fillna(0).astype('float32')

    # 時系列分割: 最後の20%をテストに
    df_sorted = df.sort_values(by=['today_race_date', 'race_id']).reset_index(drop=True)
    unique_races = df_sorted[['today_race_date', 'race_id']].drop_duplicates().sort_values(by=['today_race_date', 'race_id'])
    n_races = len(unique_races)
    split_idx = int(n_races * 0.8)
    train_races = set(unique_races.iloc[:split_idx]['race_id'])
    test_races = set(unique_races.iloc[split_idx:]['race_id'])

    train_mask = df['race_id'].isin(train_races)
    test_mask = df['race_id'].isin(test_races)

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    df_test = df[test_mask].copy()

    g_train = df[train_mask].groupby('race_id').size().tolist()
    g_test = df[test_mask].groupby('race_id').size().tolist()

    logger.info(f"Train: {len(X_train)} rows ({len(train_races)} races), Test: {len(X_test)} rows ({len(test_races)} races)")

    params = {
        'objective': 'lambdarank',
        'metric': 'ndcg',
        'ndcg_at': [1, 3, 5],
        'learning_rate': 0.03,
        'num_leaves': 15,
        'max_depth': 4,
        'min_data_in_leaf': 20,
        'bagging_fraction': 0.8,
        'bagging_freq': 1,
        'feature_fraction': 0.8,
        'lambda_l2': 5.0,
        'verbosity': -1,
        'n_jobs': -1,
        'seed': 42,
    }

    train_data = lgb.Dataset(X_train, label=y_train, categorical_feature=cat_cols, group=g_train)
    test_data = lgb.Dataset(X_test, label=y_test, categorical_feature=cat_cols, group=g_test)

    model = lgb.train(
        params, train_data,
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        num_boost_round=2000,
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)],
    )

    logger.info(f"Best iteration: {model.best_iteration}")

    # テスト予測
    test_preds = model.predict(X_test, num_iteration=model.best_iteration)
    df_test = df_test.copy()
    df_test['pred_score'] = test_preds

    # 過学習チェック
    train_preds = model.predict(X_train, num_iteration=model.best_iteration)
    train_ndcg = _group_ndcg(y_train.values, train_preds, g_train, k=3)
    test_ndcg = _group_ndcg(y_test.values, test_preds, g_test, k=3)
    logger.info(f"Train NDCG@3: {train_ndcg:.4f}, Test NDCG@3: {test_ndcg:.4f}, 比率: {test_ndcg/train_ndcg:.3f}")

    return model, df_test, feature_cols, train_ndcg, test_ndcg


def _group_ndcg(y_true, y_pred, groups, k=3):
    from sklearn.metrics import ndcg_score
    scores = []
    start = 0
    for g in groups:
        end = start + g
        gt = y_true[start:end]
        pr = y_pred[start:end]
        if len(gt) > 1:
            try:
                s = ndcg_score([gt], [pr], k=min(k, len(gt)))
                scores.append(s)
            except Exception:
                pass
        start = end
    return float(np.mean(scores)) if scores else 0.0


# ─── ROI シミュレーション ────────────────────────────────────────────────────
def simulate_roi(df_test: pd.DataFrame) -> dict:
    """
    各レースの予測上位N頭で各馬券を購入した場合のROIを計算する。
    BET_UNIT円ずつ賭ける。
    """
    BET_UNIT = 100  # 1点あたり100円

    results = {
        '単勝': {'bet': 0, 'win': 0, 'hit': 0, 'total': 0},
        '複勝': {'bet': 0, 'win': 0, 'hit': 0, 'total': 0},
        '馬連': {'bet': 0, 'win': 0, 'hit': 0, 'total': 0},
        '馬単': {'bet': 0, 'win': 0, 'hit': 0, 'total': 0},
        '3連複': {'bet': 0, 'win': 0, 'hit': 0, 'total': 0},
        '3連単': {'bet': 0, 'win': 0, 'hit': 0, 'total': 0},
    }

    for race_id, group in df_test.groupby('race_id'):
        group = group.sort_values('pred_score', ascending=False).reset_index(drop=True)

        # 実際の結果
        actual_1st = group[group['rank_int'] == 1]['horse_number'].values
        actual_2nd = group[group['rank_int'] == 2]['horse_number'].values
        actual_3rd = group[group['rank_int'] == 3]['horse_number'].values
        if len(actual_1st) == 0 or len(actual_2nd) == 0 or len(actual_3rd) == 0:
            continue

        a1 = str(actual_1st[0])
        a2 = str(actual_2nd[0])
        a3 = str(actual_3rd[0])

        # 払戻金 (race内で共通)
        def get_pay(col):
            vals = group[col].dropna()
            if len(vals) == 0:
                return None
            try:
                return float(str(vals.iloc[0]).replace(',', ''))
            except Exception:
                return None

        pay1 = get_pay('pay1')
        pay123_1 = get_pay('pay123_1')
        pay123_2 = get_pay('pay123_2')
        pay123_3 = get_pay('pay123_3')
        pay12_21 = get_pay('pay12_21')  # 馬連
        pay12_12 = get_pay('pay12_12')  # 馬単
        pay123_321 = get_pay('pay123_321')  # 3連複
        pay123_123 = get_pay('pay123_123')  # 3連単

        # 予測上位馬番
        top1 = str(group.iloc[0]['horse_number'])
        top2 = [str(group.iloc[i]['horse_number']) for i in range(min(2, len(group)))]
        top3 = [str(group.iloc[i]['horse_number']) for i in range(min(3, len(group)))]

        # ── 単勝 (top1を1着予測) ──
        if pay1 is not None:
            results['単勝']['bet'] += BET_UNIT
            results['単勝']['total'] += 1
            if top1 == a1:
                results['単勝']['win'] += pay1
                results['単勝']['hit'] += 1

        # ── 複勝 (top3の各馬を複勝購入) ──
        # 複勝: 賭けた馬が3着以内なら的中。払戻はその馬の実際着順で決まる
        # pay123_1 = 1着馬の複勝払戻, pay123_2 = 2着馬, pay123_3 = 3着馬
        actual_rank_order = [a1, a2, a3]
        pays_123 = [pay123_1, pay123_2, pay123_3]
        actual_top3_set = {a1, a2, a3}
        for h in top3:
            results['複勝']['bet'] += BET_UNIT
            results['複勝']['total'] += 1
            if h in actual_top3_set:
                idx = actual_rank_order.index(h)
                pay_val = pays_123[idx] if idx < len(pays_123) and pays_123[idx] else None
                if pay_val:
                    results['複勝']['win'] += pay_val
                    results['複勝']['hit'] += 1

        # ── 馬連 (top2で2頭軸ボックス) ──
        if len(top2) >= 2 and pay12_21 is not None:
            results['馬連']['bet'] += BET_UNIT
            results['馬連']['total'] += 1
            pred_set = set(top2[:2])
            actual_set = {a1, a2}
            if pred_set == actual_set:
                results['馬連']['win'] += pay12_21
                results['馬連']['hit'] += 1

        # ── 馬単 (top1→top2の2連単) ──
        if len(top2) >= 2 and pay12_12 is not None:
            results['馬単']['bet'] += BET_UNIT
            results['馬単']['total'] += 1
            if top2[0] == a1 and top2[1] == a2:
                results['馬単']['win'] += pay12_12
                results['馬単']['hit'] += 1

        # ── 3連複 (top3ボックス) ──
        if len(top3) >= 3 and pay123_321 is not None:
            results['3連複']['bet'] += BET_UNIT
            results['3連複']['total'] += 1
            if set(top3[:3]) == {a1, a2, a3}:
                results['3連複']['win'] += pay123_321
                results['3連複']['hit'] += 1

        # ── 3連単 (top3の順番通り) ──
        if len(top3) >= 3 and pay123_123 is not None:
            results['3連単']['bet'] += BET_UNIT
            results['3連単']['total'] += 1
            if top3[0] == a1 and top3[1] == a2 and top3[2] == a3:
                results['3連単']['win'] += pay123_123
                results['3連単']['hit'] += 1

    return results


def print_roi_table(results: dict, train_ndcg: float, test_ndcg: float):
    """ROI結果をフォーマット出力する。"""
    print("\n" + "="*70)
    print("  競馬予測 ROI (回収率) シミュレーション結果")
    print("="*70)
    print(f"  Train NDCG@3: {train_ndcg:.4f}  Test NDCG@3: {test_ndcg:.4f}")
    print(f"  過学習比率: {test_ndcg/train_ndcg:.3f} (1.0に近いほど良)")
    print("-"*70)
    print(f"  {'買い方':<8} {'賭金(円)':>10} {'回収(円)':>10} {'回収率':>8} {'的中数':>8} {'的中率':>8}")
    print("-"*70)

    for bet_type, data in results.items():
        bet = data['bet']
        win = data['win']
        hit = data['hit']
        total = data['total']
        roi = (win / bet * 100) if bet > 0 else 0
        hit_rate = (hit / total * 100) if total > 0 else 0
        print(f"  {bet_type:<8} {bet:>10,} {win:>10,.0f} {roi:>7.1f}% {hit:>8} {hit_rate:>7.1f}%")

    print("="*70)
    print()


def main():
    logger.info("=== ROI分析パイプライン開始 ===")

    # 1. データ読み込み
    df = load_data()

    # 2. ML学習
    model, df_test, feature_cols, train_ndcg, test_ndcg = train_model(df)

    # 3. ROIシミュレーション
    logger.info("ROIシミュレーション実行中...")
    roi_results = simulate_roi(df_test)

    # 4. 結果出力
    print_roi_table(roi_results, train_ndcg, test_ndcg)

    # 5. Feature Importance Top 20
    importance = dict(zip(feature_cols, model.feature_importance(importance_type='gain')))
    top20 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:20]
    print("特徴量重要度 Top 20:")
    for rank, (feat, imp) in enumerate(top20, 1):
        print(f"  {rank:2}. {feat:<30} {imp:.1f}")

    # 6. テストレース数サマリ
    test_races = df_test['race_id'].nunique()
    print(f"\n  テストレース数: {test_races}")
    print(f"  学習レース数: {df[df['race_id'].isin(set(df['race_id']) - set(df_test['race_id']))]['race_id'].nunique()}")


if __name__ == "__main__":
    main()
