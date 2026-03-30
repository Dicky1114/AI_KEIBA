#!/usr/bin/env python3
"""
@file    run_full_pipeline.py
@brief   5年分データ収集 → 学習データ構築 → CSV出力 → ML学習の統合パイプライン
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)

使用方法:
    # venv有効化後
    # 全パイプライン（スクレイピング + 学習データ構築 + CSV + ML）
    python scripts/run_full_pipeline.py --start 2021 --end 2026

    # 学習データ構築のみ（スクレイピング済みデータから）
    python scripts/run_full_pipeline.py --skip-scrape

    # ML学習のみ（CSV既存）
    python scripts/run_full_pipeline.py --ml-only

    # スクレイピングのみ（特定年度）
    python scripts/run_full_pipeline.py --scrape-only --year 2023
"""

import os
import sys
import argparse
import uuid
import csv
import logging
import time
from datetime import date

# Django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from django.conf import settings
from django.db import connection
from django.utils.timezone import localtime, now
from django.forms.models import model_to_dict

from app_folder.models import URLMst, BaseData, ResultData, HorseData, JockeyData, TrainingInfo
from app_folder.services.tasks import (
    run_local_race_task, run_local_horse_task, run_local_jockey_task,
    ensure_media_dirs,
)
from app_folder.services.insert_db import (
    insert_final_base_info, insert_final_horse_info,
    insert_final_jockey_info, insert_final_result_info,
    insert_training_info,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


def create_views():
    """必要なDBビューを作成する。"""
    views_sql = [
        '''CREATE OR REPLACE VIEW v_compare_base_result AS
        SELECT DISTINCT b.race_id, b.horse_number, b.race_date
        FROM t_base_info b
        INNER JOIN t_result_info r ON b.race_id = r.race_id AND b.horse_number = r.horse_number''',

        '''CREATE OR REPLACE VIEW v_create_race_ids AS
        SELECT u.race_id, u.url
        FROM m_url u
        LEFT JOIN t_base_info b ON u.race_id = b.race_id
        WHERE b.race_id IS NULL''',

        '''CREATE OR REPLACE VIEW v_weekend AS
        SELECT DISTINCT
            u.race_date::date AS race_date,
            u.race_date::date AS race_date_null,
            u.race_id
        FROM m_url u''',

        '''CREATE OR REPLACE VIEW v_compare_base_horse AS
        SELECT DISTINCT b.race_id, b.horse_number, b.horse_url
        FROM t_base_info b
        WHERE b.horse_url IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM t_horse_info h WHERE h.horse_id = SUBSTRING(b.horse_url FROM '/horse/([^/]+)')
        )''',

        '''CREATE OR REPLACE VIEW v_compare_base_jockey AS
        SELECT DISTINCT b.race_id, b.horse_number, b.jockey_url
        FROM t_base_info b
        WHERE b.jockey_url IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM t_jockey_info j WHERE j.jockey_id = SUBSTRING(b.jockey_url FROM '/jockey/result/recent/([^/]+)')
        )''',
    ]

    with connection.cursor() as cursor:
        for sql in views_sql:
            try:
                cursor.execute(sql)
            except Exception as e:
                logger.warning(f"View作成エラー (無視して続行): {e}")


def step1_scrape_races(start_year: int, end_year: int):
    """年度ごとにレースURL + base + result をスクレイピングする。"""
    for year in range(start_year, end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        # 今年は今日まで
        today = date.today()
        if year == today.year:
            end_date = today.isoformat()

        logger.info(f"=== {year}年 スクレイピング開始 ({start_date} ~ {end_date}) ===")

        task_id = f"batch-{year}-{uuid.uuid4().hex[:8]}"
        try:
            result = run_local_race_task(task_id, 'batch_scraper', start_date, end_date)
            logger.info(f"  {year}年 完了: {result}")
        except Exception as e:
            logger.error(f"  {year}年 エラー: {e}")
            import traceback
            traceback.print_exc()
            # エラーでも続行
            continue

        # 中間進捗
        logger.info(f"  URLMst: {URLMst.objects.count()}, "
                     f"BaseData: {BaseData.objects.count()}, "
                     f"ResultData: {ResultData.objects.count()}")


def step2_scrape_horse():
    """馬履歴をスクレイピングする。"""
    logger.info("=== 馬履歴スクレイピング ===")
    task_id = f"batch-horse-{uuid.uuid4().hex[:8]}"
    try:
        result = run_local_horse_task(task_id, 'batch_scraper')
        logger.info(f"  馬履歴完了: {result}")
    except Exception as e:
        logger.error(f"  馬履歴エラー: {e}")
        import traceback
        traceback.print_exc()

    logger.info(f"  HorseData: {HorseData.objects.count()}")


def step3_scrape_jockey():
    """騎手履歴をスクレイピングする。"""
    logger.info("=== 騎手履歴スクレイピング ===")
    task_id = f"batch-jockey-{uuid.uuid4().hex[:8]}"
    try:
        result = run_local_jockey_task(task_id, 'batch_scraper')
        logger.info(f"  騎手履歴完了: {result}")
    except Exception as e:
        logger.error(f"  騎手履歴エラー: {e}")
        import traceback
        traceback.print_exc()

    logger.info(f"  JockeyData: {JockeyData.objects.count()}")


def step4_build_training_data():
    """finalテーブル → trainingテーブルを構築する。"""
    logger.info("=== 学習データ構築 ===")

    steps = [
        ("final_base_info", insert_final_base_info),
        ("final_horse_info", insert_final_horse_info),
        ("final_jockey_info", insert_final_jockey_info),
        ("final_result_info", insert_final_result_info),
        ("training_info", insert_training_info),
    ]

    for name, func in steps:
        logger.info(f"  {name} 構築中...")
        try:
            func()
            logger.info(f"  {name} 完了")
        except Exception as e:
            logger.error(f"  {name} エラー: {e}")
            import traceback
            traceback.print_exc()

    logger.info(f"  TrainingInfo: {TrainingInfo.objects.count()} レコード")


def step5_export_csv() -> str:
    """TrainingInfoからCSVを出力する。"""
    logger.info("=== CSV出力 ===")

    csv_dir = os.path.join(settings.MEDIA_ROOT, "csv_export")
    os.makedirs(csv_dir, exist_ok=True)
    csv_name = f"train_data_{localtime(now()).strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path = os.path.join(csv_dir, csv_name)

    queryset = TrainingInfo.objects.all().order_by('today_race_date', 'race_id', 'horse_number')
    count = queryset.count()

    if count == 0:
        logger.error("TrainingInfo が空です。CSV出力をスキップします。")
        return ""

    # 全フィールドを取得
    fields = [f.name for f in TrainingInfo._meta.get_fields() if hasattr(f, 'column')]
    # result系カラムも含める（rankが必要）
    selected = ['id'] + [f for f in fields if f != 'id']

    with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=selected)
        writer.writeheader()
        for idx, row in enumerate(queryset.iterator(chunk_size=1000), start=1):
            row_dict = model_to_dict(row)
            output_row = {k: row_dict.get(k, "") for k in selected}
            output_row["id"] = idx
            writer.writerow(output_row)

    logger.info(f"  CSV出力完了: {csv_path} ({count} レコード)")
    return csv_path


def step6_ml_training(csv_path: str, optimize: bool = True):
    """ML学習パイプラインを実行する。"""
    logger.info("=== ML学習パイプライン ===")

    from app_folder.services.ml_training import run_full_pipeline

    output_dir = os.path.join(settings.MEDIA_ROOT, "ml_output")

    result = run_full_pipeline(
        csv_path=csv_path,
        output_dir=output_dir,
        optimize=optimize,
    )

    logger.info(f"  テストNDCG@3: {result['result']['test_ndcg3']:.4f}")
    logger.info(f"  analysis.md: {result['analysis_path']}")
    logger.info(f"  馬単予測数: {len(result['exacta_predictions'])} レース")

    # 上位5件表示
    for pred in result['exacta_predictions'][:5]:
        logger.info(f"  レース {pred['race_id']}: Top3={pred['top3_horses']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="競馬データ 統合パイプライン")
    parser.add_argument('--start', type=int, default=2021, help='開始年度')
    parser.add_argument('--end', type=int, default=2026, help='終了年度')
    parser.add_argument('--year', type=int, default=None, help='特定年度のみスクレイピング')
    parser.add_argument('--skip-scrape', action='store_true', help='スクレイピングをスキップ')
    parser.add_argument('--scrape-only', action='store_true', help='スクレイピングのみ実行')
    parser.add_argument('--ml-only', action='store_true', help='ML学習のみ実行（既存CSV使用）')
    parser.add_argument('--no-optimize', action='store_true', help='Optuna最適化をスキップ')
    parser.add_argument('--csv', type=str, default=None, help='既存CSVファイルパス')
    args = parser.parse_args()

    start_time = time.time()
    logger.info("==== 統合パイプライン開始 ====")

    # ビュー作成
    create_views()

    if args.ml_only:
        # ML学習のみ
        csv_path = args.csv
        if not csv_path:
            import glob
            csv_dir = os.path.join(settings.MEDIA_ROOT, "csv_export")
            csvs = glob.glob(os.path.join(csv_dir, "train_data_*.csv"))
            csv_path = max(csvs, key=os.path.getmtime) if csvs else None
        if not csv_path:
            logger.error("CSVが見つかりません")
            sys.exit(1)
        step6_ml_training(csv_path, optimize=not args.no_optimize)
    else:
        # スクレイピング
        if not args.skip_scrape:
            start_year = args.year or args.start
            end_year = args.year or args.end
            step1_scrape_races(start_year, end_year)
            step2_scrape_horse()
            step3_scrape_jockey()

        if args.scrape_only:
            logger.info("スクレイピングのみ完了")
        else:
            # 学習データ構築 → CSV → ML
            step4_build_training_data()
            csv_path = step5_export_csv()
            if csv_path:
                step6_ml_training(csv_path, optimize=not args.no_optimize)

    elapsed = time.time() - start_time
    logger.info(f"==== 統合パイプライン完了 ({elapsed/60:.1f}分) ====")


if __name__ == '__main__':
    main()
