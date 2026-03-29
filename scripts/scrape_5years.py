#!/usr/bin/env python3
"""
@file    scrape_5years.py
@brief   過去5年分のレースデータを一括スクレイピングするバッチスクリプト
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)

使用方法:
    # venv有効化後
    python scripts/scrape_5years.py --start 2021-01-01 --end 2026-03-30

    # 特定年度のみ
    python scripts/scrape_5years.py --year 2024

    # ドライラン（URL生成のみ、DB保存しない）
    python scripts/scrape_5years.py --year 2024 --dry-run
"""

import os
import sys
import argparse
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from app_folder.services.get_raceid import GetRaceID
from app_folder.services.insert_db import insert_url_db
from app_folder.models import URLMst, CompareView, CreateRaceIDsView
from app_folder.services.tasks import create_base_task, create_horse_task, create_jockey_task

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from django.conf import settings
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

SYSTEM_USER = "batch_scraper"
SLEEP_PER_MONTH = 2  # 月切替時のウェイト秒


def create_driver():
    """ヘッドレスChromeドライバーを作成する。"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=chrome_options)


def ensure_media_dirs():
    """メディアディレクトリを作成する。"""
    for subdir in ["", "base", "odds", "horse", "jockey", "calendar_yyyymm", "calendar_yyyymmdd", "csv_export"]:
        path = os.path.join(settings.MEDIA_ROOT, subdir)
        os.makedirs(path, exist_ok=True)


def generate_month_ranges(start_date, end_date):
    """
    開始日から終了日まで月単位でレンジを生成する。
    @param  start_date 開始日 (datetime.date)
    @param  end_date 終了日 (datetime.date)
    @yields (month_start, month_end) tuples
    """
    current = start_date.replace(day=1)
    while current <= end_date:
        month_end = (current + relativedelta(months=1)) - timedelta(days=1)
        if month_end > end_date:
            month_end = end_date
        yield current, month_end
        current = current + relativedelta(months=1)


def scrape_month(driver, start_date, end_date, dry_run=False):
    """
    1ヶ月分のレースURLを取得しDBに保存する。
    @param  driver Chrome WebDriver
    @param  start_date 月初日
    @param  end_date 月末日
    @param  dry_run True=URL生成のみ
    @returns int 取得レース数
    """
    race_service = GetRaceID()

    try:
        url_list, race_id_list, dates_list = race_service.create_url_list(
            start_date, end_date, driver
        )
    except Exception as e:
        logger.error(f"URL取得失敗 ({start_date} - {end_date}): {e}")
        return 0

    if url_list == "sys_err" or not url_list:
        logger.warning(f"レースなし ({start_date} - {end_date})")
        return 0

    url_df = pd.DataFrame({
        "race_id": race_id_list,
        "race_date": dates_list,
        "url": url_list,
    }).drop_duplicates(subset=["race_id"]).sort_values("race_date").reset_index(drop=True)

    logger.info(f"  {start_date} - {end_date}: {len(url_df)} レース検出")

    if dry_run:
        return len(url_df)

    # DB保存
    result = insert_url_db(url_df, SYSTEM_USER)
    if result == "sys_err":
        logger.error(f"DB保存失敗 ({start_date} - {end_date})")
        return 0

    return len(url_df)


def scrape_race_details(driver, dry_run=False):
    """
    未取得レースの詳細情報をスクレイピングする。
    @param  driver Chrome WebDriver
    @param  dry_run True=スキップ
    @returns int 処理レース数
    """
    if dry_run:
        logger.info("[Dry-run] レース詳細スクレイピングをスキップ")
        return 0

    # 未取得URLを検出
    url_race_id_pairs = URLMst.objects.exclude(
        race_id__in=CompareView.objects.values("race_id")
    ).order_by("race_id").values_list("url", "race_id")

    if not url_race_id_pairs:
        logger.info("全レース取得済み")
        return 0

    logger.info(f"未取得レース: {len(url_race_id_pairs)} 件")

    # Celeryタスクで非同期処理
    task = create_base_task.apply_async(
        args=[SYSTEM_USER, list(url_race_id_pairs)],
        countdown=5,
    )
    logger.info(f"レース詳細スクレイピングタスク開始: {task.id}")
    return len(url_race_id_pairs)


def main():
    parser = argparse.ArgumentParser(description="過去5年分の競馬データスクレイピング")
    parser.add_argument('--start', type=str, help='開始日 (YYYY-MM-DD)', default=None)
    parser.add_argument('--end', type=str, help='終了日 (YYYY-MM-DD)', default=None)
    parser.add_argument('--year', type=int, help='特定年度のみ', default=None)
    parser.add_argument('--dry-run', action='store_true', help='URL生成のみ（DB保存しない）')
    parser.add_argument('--skip-details', action='store_true', help='レース詳細スクレイピングをスキップ')
    args = parser.parse_args()

    # 日付範囲決定
    if args.year:
        start_date = datetime(args.year, 1, 1).date()
        end_date = datetime(args.year, 12, 31).date()
    elif args.start and args.end:
        start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end, '%Y-%m-%d').date()
    else:
        # デフォルト: 5年分
        end_date = datetime.today().date()
        start_date = (end_date - timedelta(days=365 * 5))

    logger.info(f"==== 5年分スクレイピング開始 ====")
    logger.info(f"期間: {start_date} ~ {end_date}")
    logger.info(f"Dry-run: {args.dry_run}")

    ensure_media_dirs()
    driver = create_driver()

    total_races = 0
    try:
        for month_start, month_end in generate_month_ranges(start_date, end_date):
            logger.info(f"[{month_start.strftime('%Y-%m')}] 処理中...")
            count = scrape_month(driver, month_start, month_end, dry_run=args.dry_run)
            total_races += count
            time.sleep(SLEEP_PER_MONTH)

        logger.info(f"URL取得完了: 合計 {total_races} レース")

        # レース詳細
        if not args.skip_details:
            scrape_race_details(driver, dry_run=args.dry_run)

    except KeyboardInterrupt:
        logger.info("中断されました")
    except Exception as e:
        logger.error(f"エラー: {e}", exc_info=True)
    finally:
        driver.quit()

    logger.info(f"==== スクレイピング完了: {total_races} レース ====")


if __name__ == '__main__':
    main()
