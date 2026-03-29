#!/usr/bin/env python3
"""
@file    run_training.py
@brief   ML学習パイプライン実行スクリプト
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)

使用方法:
    # 基本実行（最新CSV使用）
    python scripts/run_training.py

    # 特定CSVファイル指定
    python scripts/run_training.py --csv path/to/train.csv

    # Optuna最適化付き
    python scripts/run_training.py --optimize

    # 特徴量選択のみ
    python scripts/run_training.py --feature-select-only
"""

import os
import sys
import argparse
import glob
import logging

# Django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from django.conf import settings
from app_folder.services.ml_training import (
    run_full_pipeline,
    load_training_csv,
    prepare_data,
    remove_correlated_features,
    forward_feature_selection,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


def find_latest_csv():
    """最新のトレーニングCSVを検索する。"""
    csv_dir = os.path.join(settings.MEDIA_ROOT, "csv_export")
    if not os.path.exists(csv_dir):
        return None
    csv_files = glob.glob(os.path.join(csv_dir, "train_data_*.csv"))
    return max(csv_files, key=os.path.getmtime) if csv_files else None


def main():
    parser = argparse.ArgumentParser(description="競馬予測ML学習パイプライン")
    parser.add_argument('--csv', type=str, help='学習CSVファイルパス', default=None)
    parser.add_argument('--optimize', action='store_true', help='Optunaパラメータ最適化を実行')
    parser.add_argument('--feature-select-only', action='store_true', help='特徴量選択のみ実行')
    parser.add_argument('--output', type=str, help='出力ディレクトリ', default=None)
    args = parser.parse_args()

    # CSV検索
    csv_path = args.csv or find_latest_csv()
    if not csv_path or not os.path.exists(csv_path):
        logger.error("学習CSVが見つかりません。--csv オプションで指定してください。")
        sys.exit(1)

    logger.info(f"学習CSV: {csv_path}")

    # 出力先
    output_dir = args.output or os.path.join(settings.MEDIA_ROOT, "ml_output")

    if args.feature_select_only:
        # 特徴量選択のみ
        df = load_training_csv(csv_path)
        X, y, groups_df, categorical_cols = prepare_data(df)

        # 相関除去
        corr_drop = remove_correlated_features(X)
        if corr_drop:
            X = X.drop(columns=corr_drop)
            categorical_cols = [c for c in categorical_cols if c not in corr_drop]
            logger.info(f"相関除去: {len(corr_drop)} features")

        selected, log = forward_feature_selection(
            X, y, groups_df, categorical_cols, max_features=30, n_splits=3
        )
        logger.info(f"選択特徴量 ({len(selected)}): {selected}")
        for entry in log:
            logger.info(f"  Step {entry['step']}: +{entry['feature']} → NDCG@3={entry['ndcg@3']:.4f}")
        return

    # 全パイプライン実行
    result = run_full_pipeline(
        csv_path=csv_path,
        output_dir=output_dir,
        optimize=args.optimize,
    )

    logger.info(f"学習完了!")
    logger.info(f"  テストNDCG@3: {result['result']['test_ndcg3']:.4f}")
    logger.info(f"  analysis.md: {result['analysis_path']}")
    logger.info(f"  馬単予測数: {len(result['exacta_predictions'])} レース")

    # 馬単予測サンプル表示
    for pred in result['exacta_predictions'][:5]:
        logger.info(f"  レース {pred['race_id']}: Top3={pred['top3_horses']} → {pred['exacta_combinations']}")


if __name__ == '__main__':
    main()
