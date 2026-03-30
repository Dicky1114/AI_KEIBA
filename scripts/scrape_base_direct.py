#!/usr/bin/env python3
"""
@file    scrape_base_direct.py
@brief   既存URLMstから直接レースbase+resultをスクレイピング（カレンダー再取得不要）
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)

URLMst に既に保存済みのURLからbase/result情報を取得してDBに保存する。
5年分の全URLスクレイピング→学習データ構築→CSV出力→ML学習までを一括実行。

使用方法:
    # 全URL取得 + 学習
    python scripts/scrape_base_direct.py

    # スクレイピングのみ（ML実行しない）
    python scripts/scrape_base_direct.py --scrape-only

    # 年度追加（2022年のURLのみスクレイピング）
    python scripts/scrape_base_direct.py --year 2022

    # ML学習のみ
    python scripts/scrape_base_direct.py --ml-only
"""

import os
import sys
import argparse
import logging
import time
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from django.conf import settings
from django.db import connection, transaction

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app_folder.models import URLMst, BaseData, ResultData, HorseData, JockeyData, TrainingInfo
from app_folder.services.get_base import get_data
from app_folder.services.get_result import result as get_result
from app_folder.services.insert_db import (
    insert_base_db, insert_result_db,
    insert_final_base_info, insert_final_horse_info,
    insert_final_jockey_info, insert_final_result_info,
    insert_training_info,
)
from app_folder.services.get_horse import horse_data
from app_folder.services.get_jockey import jockey_data
from app_folder.utils.zip import name_change

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

USERNAME = "batch_scraper"


def create_chrome_driver():
    """ヘッドレスChromeドライバーを作成する。"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    user_agents = getattr(settings, 'USER_AGENTS', [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ])
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    return webdriver.Chrome(options=chrome_options)


def create_views():
    """必要なDBビューを作成する。"""
    views_sql = [
        '''CREATE OR REPLACE VIEW v_compare_base_result AS
        SELECT DISTINCT b.race_id, b.horse_number, b.race_date
        FROM t_base_info b
        INNER JOIN t_result_info r ON b.race_id = r.race_id AND b.horse_number = r.horse_number''',
        '''CREATE OR REPLACE VIEW v_create_race_ids AS
        SELECT u.race_id, u.url
        FROM m_url u LEFT JOIN t_base_info b ON u.race_id = b.race_id
        WHERE b.race_id IS NULL''',
        '''CREATE OR REPLACE VIEW v_weekend AS
        SELECT DISTINCT u.race_date::date AS race_date, u.race_date::date AS race_date_null, u.race_id FROM m_url u''',
        '''CREATE OR REPLACE VIEW v_compare_base_horse AS
        SELECT DISTINCT b.race_id, b.horse_number, b.horse_url
        FROM t_base_info b WHERE b.horse_url IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM t_horse_info h WHERE h.horse_id = SUBSTRING(b.horse_url FROM '/horse/([^/]+)'))''',
        '''CREATE OR REPLACE VIEW v_compare_base_jockey AS
        SELECT DISTINCT b.race_id, b.horse_number, b.jockey_url
        FROM t_base_info b WHERE b.jockey_url IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM t_jockey_info j WHERE j.jockey_id = SUBSTRING(b.jockey_url FROM '/jockey/result/recent/([^/]+)'))''',
    ]
    with connection.cursor() as cursor:
        for sql in views_sql:
            try:
                cursor.execute(sql)
            except Exception as e:
                logger.warning(f"View作成スキップ: {e}")


def get_pending_urls(year=None):
    """まだbase_infoに未登録のURLを取得する。"""
    existing_race_ids = set(BaseData.objects.values_list('race_id', flat=True).distinct())
    queryset = URLMst.objects.all().order_by('race_date', 'race_id')
    if year:
        queryset = queryset.filter(race_id__startswith=str(year))

    pending = []
    for url_obj in queryset:
        if url_obj.race_id not in existing_race_ids:
            pending.append((url_obj.url, url_obj.race_id))
    return pending


def scrape_base_result(pending_pairs):
    """base + result をスクレイピングしてDBに保存する。"""
    if not pending_pairs:
        logger.info("全レース取得済み")
        return

    logger.info(f"未取得レース: {len(pending_pairs)} 件")
    driver = create_chrome_driver()
    success = 0
    errors = 0
    skipped = 0

    try:
        for i, (url, race_id) in enumerate(pending_pairs):
            if (i + 1) % 50 == 0:
                logger.info(f"  進捗: {i+1}/{len(pending_pairs)} (成功:{success} エラー:{errors} スキップ:{skipped})")

            with transaction.atomic():
                try:
                    base_df, html_content, base_flg = get_data(url, race_id, driver)
                    result_df, kaisai_date, result_flg = get_result(url, race_id, "")

                    if html_content == "skip":
                        skipped += 1
                        transaction.set_rollback(True)
                        continue
                    if html_content == "error":
                        errors += 1
                        transaction.set_rollback(True)
                        continue

                    if len(base_df) != len(result_df):
                        skipped += 1
                        transaction.set_rollback(True)
                        continue

                    insert_base_db(base_df, USERNAME)
                    insert_result_db(result_df, USERNAME)

                    if base_flg:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, "base")
                    if result_flg:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, "odds")

                    success += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        logger.warning(f"  レース {race_id} エラー: {e}")
                    transaction.set_rollback(True)
                    continue

            # レート制限対策
            if (i + 1) % 10 == 0:
                time.sleep(0.5)

    finally:
        driver.quit()

    logger.info(f"base+result完了: 成功={success} エラー={errors} スキップ={skipped}")


def scrape_horse_direct():
    """馬履歴を同期的にスクレイピングする。"""
    # media/horse のHTMLを展開
    horse_dir = os.path.join(settings.MEDIA_ROOT, "horse")
    os.makedirs(horse_dir, exist_ok=True)

    # v_compare_base_horse から未取得馬URLを取得
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT horse_url FROM v_compare_base_horse LIMIT 10000")
        pending_urls = [row[0] for row in cursor.fetchall()]

    if not pending_urls:
        logger.info("全馬履歴取得済み")
        return

    logger.info(f"未取得馬: {len(pending_urls)} 件")

    # horse_data関数はTaskContextを必要とするため、ダミーを使う
    class DummyTask:
        class request:
            id = "batch-horse"
        def update_state(self, **kwargs):
            pass

    try:
        horse_data(DummyTask(), "html_content", USERNAME, "horse")
    except Exception as e:
        logger.warning(f"馬履歴エラー (続行): {e}")


def scrape_jockey_direct():
    """騎手履歴を同期的にスクレイピングする。"""
    jockey_dir = os.path.join(settings.MEDIA_ROOT, "jockey")
    os.makedirs(jockey_dir, exist_ok=True)

    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT jockey_url FROM v_compare_base_jockey LIMIT 10000")
        pending_urls = [row[0] for row in cursor.fetchall()]

    if not pending_urls:
        logger.info("全騎手履歴取得済み")
        return

    logger.info(f"未取得騎手: {len(pending_urls)} 件")

    try:
        jockey_data("html_content", USERNAME, "jockey")
    except Exception as e:
        logger.warning(f"騎手履歴エラー (続行): {e}")


def build_training_and_csv():
    """finalテーブル構築 → training → CSV出力。"""
    import csv as csv_mod
    from django.utils.timezone import localtime, now
    from django.forms.models import model_to_dict

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

    count = TrainingInfo.objects.count()
    logger.info(f"  TrainingInfo: {count} レコード")

    if count == 0:
        logger.error("TrainingInfo が空。CSV出力スキップ。")
        return ""

    csv_dir = os.path.join(settings.MEDIA_ROOT, "csv_export")
    os.makedirs(csv_dir, exist_ok=True)
    csv_name = f"train_data_{localtime(now()).strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path = os.path.join(csv_dir, csv_name)

    fields = [f.name for f in TrainingInfo._meta.get_fields() if hasattr(f, 'column')]
    selected = ['id'] + [f for f in fields if f != 'id']

    with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv_mod.DictWriter(f, fieldnames=selected)
        writer.writeheader()
        for idx, row in enumerate(TrainingInfo.objects.all().order_by('today_race_date', 'race_id', 'horse_number').iterator(chunk_size=1000), start=1):
            row_dict = model_to_dict(row)
            output_row = {k: row_dict.get(k, "") for k in selected}
            output_row["id"] = idx
            writer.writerow(output_row)

    logger.info(f"  CSV出力: {csv_path} ({count} レコード)")
    return csv_path


def run_ml(csv_path, optimize=True):
    """ML学習パイプラインを実行する。"""
    from app_folder.services.ml_training import run_full_pipeline

    output_dir = os.path.join(settings.MEDIA_ROOT, "ml_output")
    result = run_full_pipeline(csv_path=csv_path, output_dir=output_dir, optimize=optimize)

    logger.info(f"  テストNDCG@3: {result['result']['test_ndcg3']:.4f}")
    logger.info(f"  analysis.md: {result['analysis_path']}")
    return result


def add_years_urls(start_year, end_year):
    """年度のURLを追加取得（URLMstにない年度のみ）。"""
    from app_folder.services.get_raceid import GetRaceID
    from app_folder.services.insert_db import insert_url_db
    from datetime import date, timedelta
    import pandas as pd
    from django.utils import timezone

    for year in range(start_year, end_year + 1):
        existing = URLMst.objects.filter(race_id__startswith=str(year)).count()
        if existing > 0:
            logger.info(f"  {year}年: {existing} URL既存 → スキップ")
            continue

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        today = date.today()
        if year == today.year:
            end_date = today

        logger.info(f"  {year}年 URL取得中...")
        driver = create_chrome_driver()
        try:
            race_service = GetRaceID()
            url_list, race_id_list, dates_list = race_service.create_url_list(start_date, end_date, driver)
            if url_list == "sys_err" or not url_list:
                logger.warning(f"  {year}年 URL取得失敗")
                continue

            url_df = pd.DataFrame({
                "race_id": race_id_list, "race_date": dates_list, "url": url_list
            }).drop_duplicates(subset=["race_id"]).sort_values("race_date").reset_index(drop=True)

            insert_url_db(url_df, USERNAME)
            logger.info(f"  {year}年 {len(url_df)} URL保存")
        except Exception as e:
            logger.error(f"  {year}年 エラー: {e}")
        finally:
            driver.quit()


def main():
    parser = argparse.ArgumentParser(description="直接base+resultスクレイピング + ML学習")
    parser.add_argument('--year', type=int, default=None, help='特定年度のみ')
    parser.add_argument('--scrape-only', action='store_true', help='スクレイピングのみ')
    parser.add_argument('--ml-only', action='store_true', help='ML学習のみ')
    parser.add_argument('--no-optimize', action='store_true', help='Optuna最適化スキップ')
    parser.add_argument('--add-years', type=str, default=None, help='URL追加年度範囲 (例: 2022-2025)')
    parser.add_argument('--csv', type=str, default=None, help='既存CSVパス')
    args = parser.parse_args()

    start_time = time.time()
    logger.info("==== 直接スクレイピング・パイプライン開始 ====")

    create_views()
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "base"), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "odds"), exist_ok=True)

    if args.ml_only:
        csv_path = args.csv
        if not csv_path:
            import glob
            csv_dir = os.path.join(settings.MEDIA_ROOT, "csv_export")
            csvs = glob.glob(os.path.join(csv_dir, "train_data_*.csv"))
            csv_path = max(csvs, key=os.path.getmtime) if csvs else None
        if csv_path:
            run_ml(csv_path, optimize=not args.no_optimize)
        else:
            logger.error("CSVが見つかりません")
        elapsed = time.time() - start_time
        logger.info(f"==== パイプライン完了 ({elapsed/60:.1f}分) ====")
        return

    # URL追加
    if args.add_years:
        parts = args.add_years.split('-')
        add_years_urls(int(parts[0]), int(parts[1]) if len(parts) > 1 else int(parts[0]))

    # Step 1: base + result
    logger.info("=== Step 1: base + result スクレイピング ===")
    pending = get_pending_urls(year=args.year)
    scrape_base_result(pending)

    logger.info(f"  DB状態: URL={URLMst.objects.count()} Base={BaseData.objects.count()} Result={ResultData.objects.count()}")

    if args.scrape_only:
        # horse + jockey もやる
        logger.info("=== Step 2: 馬履歴スクレイピング ===")
        scrape_horse_direct()
        logger.info(f"  HorseData: {HorseData.objects.count()}")

        logger.info("=== Step 3: 騎手履歴スクレイピング ===")
        scrape_jockey_direct()
        logger.info(f"  JockeyData: {JockeyData.objects.count()}")

        elapsed = time.time() - start_time
        logger.info(f"==== スクレイピング完了 ({elapsed/60:.1f}分) ====")
        return

    # Step 2: horse + jockey
    logger.info("=== Step 2: 馬履歴スクレイピング ===")
    scrape_horse_direct()
    logger.info(f"  HorseData: {HorseData.objects.count()}")

    logger.info("=== Step 3: 騎手履歴スクレイピング ===")
    scrape_jockey_direct()
    logger.info(f"  JockeyData: {JockeyData.objects.count()}")

    # Step 4: training data build + CSV
    logger.info("=== Step 4: 学習データ構築 + CSV出力 ===")
    csv_path = build_training_and_csv()

    # Step 5: ML
    if csv_path:
        logger.info("=== Step 5: ML学習 ===")
        run_ml(csv_path, optimize=not args.no_optimize)

    elapsed = time.time() - start_time
    logger.info(f"==== パイプライン完了 ({elapsed/60:.1f}分) ====")


if __name__ == '__main__':
    main()
