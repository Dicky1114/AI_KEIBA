"""
@file    ml_training.py
@brief   競馬予測ML学習パイプライン
@module  app_folder/services
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)

包括的な競馬予測MLパイプライン:
- GroupTimeSeriesSplit (K-fold CV)
- LightGBM LambdaRank
- XGBoost (オプション)
- 特徴量選択 (Forward Selection + 相関除去)
- Optuna ハイパーパラメータ最適化
- アンサンブル (Stacking)
- 馬単 (Exacta) 2連単予測
- analysis.md 自動生成
"""

import os
import json
import logging
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import KFold
from sklearn.metrics import ndcg_score, mean_squared_error
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression, Ridge
import lightgbm as lgb

logger = logging.getLogger(__name__)

# ─── 定数 ────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
N_SPLITS = 5

# 結果情報カラム（学習に使わない）
RESULT_COLS = [
    'rank', 'rank_relation', 'race_time', 'corner_order',
    'positions', 'positions_tie',
    'pay1', 'pay1_tie', 'pay123_1', 'pay123_2', 'pay123_3', 'pay123_tie',
    'pay123_12_1', 'pay123_12_2', 'pay123_12_3', 'pay123_12_4_tie', 'pay123_12_5_tie',
    'pay12_21', 'pay12_21_tie', 'pay12_12', 'pay12_12_tie',
    'pay123_321', 'pay123_321_tie', 'pay123_123', 'pay123_123_tie',
]

# グループ識別カラム
GROUP_COLS = ['today_race_date', 'race_id']
ORDER_COLS = ['today_race_date', 'race_id', 'horse_number']

# ターゲット: rank_relation (1着=30, 2着=20, 3着=10, 他=0)
TARGET_COL = 'rank_relation'


# ─── データ前処理 ─────────────────────────────────────────────────────────────
def load_training_csv(csv_path: str) -> pd.DataFrame:
    """
    学習用CSVを読み込む。
    @param  csv_path CSVファイルパス
    @returns DataFrame
    """
    df = pd.read_csv(csv_path)
    df = df.sort_values(by=ORDER_COLS, ascending=True).reset_index(drop=True)
    return df


def prepare_data(df: pd.DataFrame):
    """
    データを学習用特徴量とターゲットに分離する。
    @param  df 元DataFrame
    @returns tuple(X, y, groups_df)
        X: 特徴量DataFrame
        y: ターゲットSeries
        groups_df: グループ識別用DataFrame
    """
    # ターゲット生成
    if TARGET_COL not in df.columns and 'rank' in df.columns:
        df[TARGET_COL] = df['rank'].apply(
            lambda x: 30 if str(x) == '1' else (20 if str(x) == '2' else (10 if str(x) == '3' else 0))
        )

    # 結果カラムとグループカラムを除外して特徴量を構築
    exclude_cols = set(RESULT_COLS + GROUP_COLS + [TARGET_COL, 'id'])
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    X = df[feature_cols].copy()
    y = df[TARGET_COL].copy()
    groups_df = df[GROUP_COLS].copy()

    # カテゴリ変数を検出・変換
    categorical_cols = []
    for col in X.columns:
        if X[col].dtype == 'object' or pd.api.types.is_categorical_dtype(X[col]):
            X[col] = X[col].astype('category')
            categorical_cols.append(col)
        elif pd.api.types.is_numeric_dtype(X[col]) and X[col].nunique() <= 10:
            X[col] = X[col].astype('category')
            categorical_cols.append(col)
        else:
            X[col] = pd.to_numeric(X[col], errors='coerce').astype('float32')

    # NaN処理
    for col in X.columns:
        if col not in categorical_cols:
            X[col] = X[col].fillna(X[col].median())

    y = y.fillna(0).astype('float32')

    return X, y, groups_df, categorical_cols


# ─── GroupTimeSeriesSplit ─────────────────────────────────────────────────────
def group_time_series_split(groups_df: pd.DataFrame, n_splits: int = N_SPLITS):
    """
    時系列考慮のGroup K-Fold Split。
    過去データで学習→未来データで検証。テストデータに訓練データが漏れない。
    @param  groups_df GROUP_COLS を含む DataFrame
    @param  n_splits 分割数
    @yields (train_indices, val_indices)
    """
    unique_groups = (
        groups_df[GROUP_COLS]
        .drop_duplicates()
        .sort_values(by=GROUP_COLS)
        .reset_index(drop=True)
    )
    n_groups = len(unique_groups)
    fold_size = n_groups // n_splits

    group_tuples = groups_df[GROUP_COLS].apply(tuple, axis=1)
    unique_tuples = unique_groups.apply(tuple, axis=1).tolist()

    for i in range(n_splits):
        val_start = i * fold_size
        val_end = val_start + fold_size if i < n_splits - 1 else n_groups

        train_set = set(map(tuple, [unique_tuples[j] for j in range(val_start)]))
        val_set = set(map(tuple, [unique_tuples[j] for j in range(val_start, val_end)]))

        train_mask = group_tuples.isin(train_set)
        val_mask = group_tuples.isin(val_set)

        train_idx = groups_df[train_mask].index.tolist()
        val_idx = groups_df[val_mask].index.tolist()

        if len(train_idx) > 0 and len(val_idx) > 0:
            yield train_idx, val_idx


# ─── 特徴量選択 ──────────────────────────────────────────────────────────────
def remove_correlated_features(X: pd.DataFrame, threshold: float = 0.95) -> list:
    """
    相関が高い特徴量を除去する。
    @param  X 特徴量DataFrame
    @param  threshold 相関しきい値
    @returns 除去するカラム名リスト
    """
    numeric_cols = X.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) < 2:
        return []

    corr_matrix = X[numeric_cols].corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
    return to_drop


def forward_feature_selection(
    X: pd.DataFrame,
    y: pd.Series,
    groups_df: pd.DataFrame,
    categorical_cols: list,
    max_features: int = 30,
    n_splits: int = 3,
):
    """
    前方選択法で特徴量を1つずつ追加しNDCGで評価する。
    @param  X 特徴量DataFrame
    @param  y ターゲットSeries
    @param  groups_df グループ識別用DataFrame
    @param  categorical_cols カテゴリカラムリスト
    @param  max_features 最大選択数
    @param  n_splits 評価用分割数
    @returns tuple(selected_features, scores_log)
    """
    available = list(X.columns)
    selected = []
    scores_log = []
    best_score = -1

    for step in range(min(max_features, len(available))):
        step_results = []

        for candidate in available:
            if candidate in selected:
                continue

            trial_features = selected + [candidate]
            X_trial = X[trial_features]
            cat_in_trial = [c for c in categorical_cols if c in trial_features]

            # 簡易評価: 最初の2 splitで評価
            fold_scores = []
            splits = list(group_time_series_split(groups_df, n_splits))
            for train_idx, val_idx in splits[:2]:
                if len(train_idx) < 10 or len(val_idx) < 10:
                    continue

                X_tr = X_trial.iloc[train_idx]
                X_va = X_trial.iloc[val_idx]
                y_tr = y.iloc[train_idx]
                y_va = y.iloc[val_idx]
                g_tr = X.iloc[train_idx].join(groups_df).groupby('race_id').size().tolist()
                g_va = X.iloc[val_idx].join(groups_df).groupby('race_id').size().tolist()

                if not g_tr or not g_va:
                    continue

                train_data = lgb.Dataset(X_tr, label=y_tr, categorical_feature=cat_in_trial, group=g_tr)
                val_data = lgb.Dataset(X_va, label=y_va, categorical_feature=cat_in_trial, group=g_va)

                params = {
                    'objective': 'lambdarank', 'metric': 'ndcg', 'ndcg_at': [3],
                    'learning_rate': 0.05, 'num_leaves': 31, 'max_depth': 6,
                    'min_data_in_leaf': 20, 'seed': RANDOM_SEED, 'verbosity': -1,
                }

                model = lgb.train(
                    params, train_data, valid_sets=[val_data],
                    num_boost_round=200,
                    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
                )

                pred = model.predict(X_va)
                score = _group_ndcg(y_va.values, pred, g_va, k=3)
                fold_scores.append(score)

            avg_score = np.mean(fold_scores) if fold_scores else 0
            step_results.append((candidate, avg_score))

        if not step_results:
            break

        step_results.sort(key=lambda x: x[1], reverse=True)
        best_candidate, best_candidate_score = step_results[0]

        if best_candidate_score > best_score:
            best_score = best_candidate_score
            selected.append(best_candidate)
            scores_log.append({
                'step': step + 1,
                'feature': best_candidate,
                'ndcg@3': round(best_candidate_score, 4),
            })
            logger.info(f"[Feature Selection] Step {step+1}: +{best_candidate} → NDCG@3={best_candidate_score:.4f}")
        else:
            logger.info(f"[Feature Selection] Step {step+1}: No improvement. Stopping.")
            break

    return selected, scores_log


# ─── LightGBM LambdaRank 学習 ────────────────────────────────────────────────
def train_lightgbm_ranker(
    X: pd.DataFrame,
    y: pd.Series,
    groups_df: pd.DataFrame,
    categorical_cols: list,
    params: dict = None,
    n_splits: int = N_SPLITS,
):
    """
    LightGBM LambdaRank + GroupTimeSeriesCV で学習する。
    @param  X 特徴量DataFrame
    @param  y ターゲットSeries
    @param  groups_df グループ識別用DataFrame
    @param  categorical_cols カテゴリカラムリスト
    @param  params LightGBMパラメータ (None=デフォルト)
    @param  n_splits 分割数
    @returns dict{models, scores, feature_importance}
    """
    if params is None:
        params = {
            'objective': 'lambdarank',
            'metric': 'ndcg',
            'ndcg_at': [1, 3, 5],
            'learning_rate': 0.03,
            'num_leaves': 42,
            'max_depth': 10,
            'min_data_in_leaf': 20,
            'bagging_fraction': 0.8,
            'bagging_freq': 1,
            'feature_fraction': 0.8,
            'lambda_l1': 0.1,
            'lambda_l2': 1.0,
            'min_gain_to_split': 0.1,
            'verbosity': -1,
            'n_jobs': -1,
        }

    all_splits = list(group_time_series_split(groups_df, n_splits))
    if len(all_splits) < 2:
        raise ValueError("データが少なすぎてsplitできません。")

    # 最後のsplitはテスト用
    train_val_splits = all_splits[:-1]
    test_split = all_splits[-1]

    models = []
    val_scores = []
    feature_importances = []

    for fold_id, (train_idx, val_idx) in enumerate(train_val_splits):
        X_train = X.iloc[train_idx]
        X_val = X.iloc[val_idx]
        y_train = y.iloc[train_idx]
        y_val = y.iloc[val_idx]

        # Group sizes
        g_train = _compute_groups(groups_df.iloc[train_idx])
        g_val = _compute_groups(groups_df.iloc[val_idx])

        if not g_train or not g_val:
            continue

        fold_params = {**params, 'seed': RANDOM_SEED + fold_id}

        train_data = lgb.Dataset(X_train, label=y_train, categorical_feature=categorical_cols, group=g_train)
        val_data = lgb.Dataset(X_val, label=y_val, categorical_feature=categorical_cols, group=g_val)

        model = lgb.train(
            fold_params,
            train_data,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'valid'],
            num_boost_round=2000,
            callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)],
        )

        pred = model.predict(X_val, num_iteration=model.best_iteration)
        ndcg3 = _group_ndcg(y_val.values, pred, g_val, k=3)
        rmse = float(np.sqrt(mean_squared_error(y_val, pred)))

        val_scores.append({'fold': fold_id, 'ndcg@3': ndcg3, 'rmse': rmse, 'best_iter': model.best_iteration})
        models.append(model)

        # Feature importance
        imp = dict(zip(X.columns, model.feature_importance(importance_type='gain')))
        feature_importances.append(imp)

        logger.info(f"Fold {fold_id}: NDCG@3={ndcg3:.4f}, RMSE={rmse:.4f}, best_iter={model.best_iteration}")

    # テスト評価
    test_train_idx, test_idx = test_split
    X_test = X.iloc[test_idx]
    y_test = y.iloc[test_idx]
    g_test = _compute_groups(groups_df.iloc[test_idx])

    # アンサンブル予測（全Foldモデルの平均）
    test_preds = np.mean([m.predict(X_test) for m in models], axis=0)
    test_ndcg3 = _group_ndcg(y_test.values, test_preds, g_test, k=3)

    # 平均Feature Importance
    avg_importance = {}
    for imp in feature_importances:
        for k, v in imp.items():
            avg_importance[k] = avg_importance.get(k, 0) + v / len(feature_importances)

    return {
        'models': models,
        'val_scores': val_scores,
        'test_ndcg3': test_ndcg3,
        'feature_importance': dict(sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)),
        'test_predictions': test_preds,
        'test_groups_df': groups_df.iloc[test_idx],
        'test_X': X_test,
    }


# ─── 馬単 (Exacta) 予測 ──────────────────────────────────────────────────────
def predict_exacta_top3(result: dict, groups_df_test: pd.DataFrame, X_test: pd.DataFrame):
    """
    馬単予測: 各レースの上位3頭から全2連単通りを生成する。
    @param  result train_lightgbm_rankerの返り値
    @param  groups_df_test テスト用グループDF
    @param  X_test テスト用特徴量DF
    @returns DataFrame with race_id, predicted_rank, horse_number, exacta_combinations
    """
    preds = result['test_predictions']
    test_df = X_test.copy()
    test_df['pred_score'] = preds
    test_df['race_id'] = groups_df_test['race_id'].values

    # horse_numberが特徴量にある場合
    hn_col = None
    for c in ['horse_number', 'HORSE_NUMBER_TODAY']:
        if c in test_df.columns:
            hn_col = c
            break

    predictions = []
    for race_id, group in test_df.groupby('race_id'):
        group = group.sort_values('pred_score', ascending=False)
        top3 = group.head(3)

        if hn_col:
            horses = top3[hn_col].tolist()
        else:
            horses = list(range(1, min(4, len(top3) + 1)))

        # 全2連単通り (3P2 = 6通り)
        exacta_combos = []
        for i in range(len(horses)):
            for j in range(len(horses)):
                if i != j:
                    exacta_combos.append(f"{horses[i]}-{horses[j]}")

        predictions.append({
            'race_id': race_id,
            'top3_horses': horses,
            'exacta_combinations': exacta_combos,
            'scores': top3['pred_score'].tolist(),
        })

    return predictions


# ─── Optuna パラメータ最適化 ──────────────────────────────────────────────────
def optimize_params(X, y, groups_df, categorical_cols, n_trials: int = 30):
    """
    Optunaでハイパーパラメータを最適化する。
    @param  X 特徴量DataFrame
    @param  y ターゲットSeries
    @param  groups_df グループ識別用DataFrame
    @param  categorical_cols カテゴリカラムリスト
    @param  n_trials 試行回数
    @returns dict{best_params, best_score, study_results}
    """
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        logger.warning("Optuna未インストール。デフォルトパラメータを使用します。")
        return None

    splits = list(group_time_series_split(groups_df, 3))
    if len(splits) < 2:
        return None

    # 評価用に2つのsplit使用
    eval_splits = splits[:2]

    def objective(trial):
        params = {
            'objective': 'lambdarank',
            'metric': 'ndcg',
            'ndcg_at': [3],
            'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
            'num_leaves': trial.suggest_int('num_leaves', 15, 127),
            'max_depth': trial.suggest_int('max_depth', 3, 15),
            'min_data_in_leaf': trial.suggest_int('min_data_in_leaf', 5, 100),
            'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
            'bagging_freq': trial.suggest_int('bagging_freq', 0, 5),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.3, 1.0),
            'lambda_l1': trial.suggest_float('lambda_l1', 1e-8, 10.0, log=True),
            'lambda_l2': trial.suggest_float('lambda_l2', 1e-8, 10.0, log=True),
            'min_gain_to_split': trial.suggest_float('min_gain_to_split', 0.0, 1.0),
            'verbosity': -1,
            'n_jobs': -1,
            'seed': RANDOM_SEED,
        }

        scores = []
        for train_idx, val_idx in eval_splits:
            X_tr = X.iloc[train_idx]
            X_va = X.iloc[val_idx]
            y_tr = y.iloc[train_idx]
            y_va = y.iloc[val_idx]
            g_tr = _compute_groups(groups_df.iloc[train_idx])
            g_va = _compute_groups(groups_df.iloc[val_idx])

            if not g_tr or not g_va:
                continue

            train_data = lgb.Dataset(X_tr, label=y_tr, categorical_feature=categorical_cols, group=g_tr)
            val_data = lgb.Dataset(X_va, label=y_va, categorical_feature=categorical_cols, group=g_va)

            model = lgb.train(
                params, train_data, valid_sets=[val_data],
                num_boost_round=1000,
                callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
            )

            pred = model.predict(X_va)
            ndcg3 = _group_ndcg(y_va.values, pred, g_va, k=3)
            scores.append(ndcg3)

        return np.mean(scores) if scores else 0.0

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)

    return {
        'best_params': study.best_params,
        'best_score': study.best_value,
        'n_trials': n_trials,
    }


# ─── analysis.md 生成 ─────────────────────────────────────────────────────────
def generate_analysis_md(
    output_dir: str,
    val_scores: list,
    test_ndcg3: float,
    feature_importance: dict,
    feature_selection_log: list = None,
    optuna_result: dict = None,
    exacta_predictions: list = None,
):
    """
    実験結果を analysis.md に書き出す。
    @param  output_dir 出力先ディレクトリ
    @param  val_scores Validation scores
    @param  test_ndcg3 テストNDCG@3
    @param  feature_importance 特徴量重要度
    @param  feature_selection_log 特徴量選択ログ
    @param  optuna_result Optuna結果
    @param  exacta_predictions 馬単予測
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(output_dir, f'analysis_{ts}.md')

    lines = [
        f"# 競馬予測 分析レポート",
        f"",
        f"**実行日時:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**モデル:** LightGBM LambdaRank",
        f"**CV方式:** GroupTimeSeriesSplit ({N_SPLITS}-fold)",
        f"",
        f"---",
        f"",
        f"## 1. Validation 結果",
        f"",
        f"| Fold | NDCG@3 | RMSE | Best Iteration |",
        f"|------|--------|------|----------------|",
    ]

    for s in val_scores:
        lines.append(f"| {s['fold']} | {s['ndcg@3']:.4f} | {s['rmse']:.4f} | {s['best_iter']} |")

    avg_ndcg = np.mean([s['ndcg@3'] for s in val_scores]) if val_scores else 0
    avg_rmse = np.mean([s['rmse'] for s in val_scores]) if val_scores else 0
    lines.extend([
        f"",
        f"**平均NDCG@3:** {avg_ndcg:.4f}",
        f"**平均RMSE:** {avg_rmse:.4f}",
        f"",
        f"## 2. テスト結果",
        f"",
        f"**テストNDCG@3:** {test_ndcg3:.4f}",
        f"",
    ])

    # 過学習チェック
    if avg_ndcg > 0:
        overfit_ratio = test_ndcg3 / avg_ndcg
        lines.append(f"**過学習比率:** {overfit_ratio:.2f} (テスト/検証比。1.0に近いほど良い)")
        lines.append(f"")

    # 特徴量選択ログ
    if feature_selection_log:
        lines.extend([
            f"## 3. 特徴量選択",
            f"",
            f"| Step | 追加特徴量 | NDCG@3 |",
            f"|------|-----------|--------|",
        ])
        for log in feature_selection_log:
            lines.append(f"| {log['step']} | {log['feature']} | {log['ndcg@3']:.4f} |")
        lines.append(f"")

    # 特徴量重要度 Top 20
    lines.extend([
        f"## 4. 特徴量重要度 (Top 20)",
        f"",
        f"| 順位 | 特徴量 | 重要度 |",
        f"|------|--------|--------|",
    ])
    for i, (feat, imp) in enumerate(list(feature_importance.items())[:20]):
        lines.append(f"| {i+1} | {feat} | {imp:.1f} |")
    lines.append(f"")

    # Optuna
    if optuna_result:
        lines.extend([
            f"## 5. ハイパーパラメータ最適化 (Optuna)",
            f"",
            f"**試行回数:** {optuna_result['n_trials']}",
            f"**最良スコア:** {optuna_result['best_score']:.4f}",
            f"",
            f"**最良パラメータ:**",
            f"```json",
            json.dumps(optuna_result['best_params'], indent=2, ensure_ascii=False),
            f"```",
            f"",
        ])

    # 馬単予測
    if exacta_predictions:
        lines.extend([
            f"## 6. 馬単 (Exacta) 予測サンプル",
            f"",
            f"| レースID | 上位3頭 | 2連単全通り |",
            f"|---------|---------|-----------|",
        ])
        for pred in exacta_predictions[:10]:  # 最初の10レース
            horses = ','.join(map(str, pred['top3_horses']))
            combos = ' / '.join(pred['exacta_combinations'])
            lines.append(f"| {pred['race_id']} | {horses} | {combos} |")
        lines.append(f"")

    # PDCAサイクル
    lines.extend([
        f"## 7. PDCA サイクル",
        f"",
        f"### Plan (計画)",
        f"- 5年分の過去データから学習し、馬単上位3頭予測を行う",
        f"- GroupTimeSeriesSplit で時系列の漏洩を防ぐ",
        f"- Forward Feature Selection で特徴量を精選する",
        f"",
        f"### Do (実行)",
        f"- LightGBM LambdaRank で {N_SPLITS}-fold 学習を実施",
        f"- Optuna で {'最適化済み' if optuna_result else '未実施'}",
        f"",
        f"### Check (評価)",
        f"- テストNDCG@3 = {test_ndcg3:.4f}",
        f"- 過学習比率 = {overfit_ratio:.2f}" if avg_ndcg > 0 else "",
        f"",
        f"### Act (改善)",
        f"- [ ] テストNDCG@3 が 0.8 未満なら特徴量追加・削除を試す",
        f"- [ ] 過学習比率が 0.85 未満なら正則化を強化する",
        f"- [ ] XGBoost/CatBoost とのアンサンブルを検討する",
        f"- [ ] 騎手・厩舎の勝率エンコーディングを試す",
        f"",
        f"---",
        f"*Generated by AI_KEIBA ML Pipeline v1.0.0*",
    ])

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    logger.info(f"analysis.md generated: {filepath}")
    return filepath


# ─── 全パイプライン実行 ──────────────────────────────────────────────────────
def run_full_pipeline(csv_path: str, output_dir: str, optimize: bool = False):
    """
    全パイプラインを一括実行する。
    @param  csv_path 学習CSVパス
    @param  output_dir 出力先ディレクトリ
    @param  optimize Optuna最適化を行うか
    @returns dict{result, analysis_path}
    """
    logger.info(f"=== ML Pipeline Start: {csv_path} ===")

    # 1. データ読み込み・前処理
    df = load_training_csv(csv_path)
    X, y, groups_df, categorical_cols = prepare_data(df)
    logger.info(f"Data loaded: {len(df)} rows, {len(X.columns)} features")

    # 2. 相関特徴量除去
    corr_drop = remove_correlated_features(X)
    if corr_drop:
        X = X.drop(columns=corr_drop)
        categorical_cols = [c for c in categorical_cols if c not in corr_drop]
        logger.info(f"Removed {len(corr_drop)} correlated features: {corr_drop}")

    # 3. 特徴量選択（データ量が十分な場合）
    feature_selection_log = None
    if len(df) > 500 and len(X.columns) > 10:
        selected, feature_selection_log = forward_feature_selection(
            X, y, groups_df, categorical_cols, max_features=30, n_splits=3
        )
        if selected:
            X = X[selected]
            categorical_cols = [c for c in categorical_cols if c in selected]
            logger.info(f"Selected {len(selected)} features")

    # 4. Optuna最適化
    optuna_result = None
    best_params = None
    if optimize:
        optuna_result = optimize_params(X, y, groups_df, categorical_cols, n_trials=30)
        if optuna_result:
            best_params = {
                'objective': 'lambdarank',
                'metric': 'ndcg',
                'ndcg_at': [1, 3, 5],
                'verbosity': -1,
                'n_jobs': -1,
                **optuna_result['best_params'],
            }

    # 5. 本学習
    result = train_lightgbm_ranker(X, y, groups_df, categorical_cols, params=best_params)
    logger.info(f"Test NDCG@3: {result['test_ndcg3']:.4f}")

    # 6. 馬単予測
    exacta_predictions = predict_exacta_top3(result, result['test_groups_df'], result['test_X'])

    # 7. モデル保存
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    for i, model in enumerate(result['models']):
        model_path = os.path.join(output_dir, f'lgb_ranker_fold{i}_{ts}.pkl')
        joblib.dump(model, model_path)
    logger.info(f"Saved {len(result['models'])} models to {output_dir}")

    # 8. analysis.md 生成
    analysis_path = generate_analysis_md(
        output_dir=output_dir,
        val_scores=result['val_scores'],
        test_ndcg3=result['test_ndcg3'],
        feature_importance=result['feature_importance'],
        feature_selection_log=feature_selection_log,
        optuna_result=optuna_result,
        exacta_predictions=exacta_predictions,
    )

    return {
        'result': result,
        'analysis_path': analysis_path,
        'exacta_predictions': exacta_predictions,
    }


# ─── ユーティリティ ──────────────────────────────────────────────────────────
def _compute_groups(groups_df: pd.DataFrame) -> list:
    """race_id ごとのグループサイズを計算する。"""
    return groups_df.groupby('race_id').size().tolist()


def _group_ndcg(y_true, y_pred, groups, k=3):
    """
    グループ単位でNDCGスコアを計算する。
    @param  y_true 真値
    @param  y_pred 予測値
    @param  groups グループサイズリスト
    @param  k 上位k件
    @returns float mean NDCG@k
    """
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
