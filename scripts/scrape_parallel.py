#!/usr/bin/env python3
"""
@file    scrape_parallel.py
@brief   並列Chromeインスタンスで高速base+resultスクレイピング
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)

4並列Chromeでbase+resultを同時スクレイピング。
単一スレッド比で3-4倍の速度。

使用方法:
    python scripts/scrape_parallel.py                # 全未取得
    python scripts/scrape_parallel.py --workers 6    # 6並列
    python scripts/scrape_parallel.py --year 2023    # 特定年度のみ
"""

import os
import sys
import argparse
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from django.conf import settings
from django.db import connection, connections

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app_folder.models import URLMst, BaseData, ResultData
from app_folder.services.get_base import get_data
from app_folder.services.get_result import result as get_result
from app_folder.services.insert_db import insert_base_db, insert_result_db
from app_folder.utils.zip import name_change

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
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


def get_pending_urls(year=None):
    """未取得URLを返す。"""
    existing = set(
        BaseData.objects.values_list('race_id', flat=True).distinct()
    )
    qs = URLMst.objects.all().order_by('race_date', 'race_id')
    if year:
        qs = qs.filter(race_id__startswith=str(year))
    return [(u.url, u.race_id) for u in qs if u.race_id not in existing]


def scrape_chunk(chunk, worker_id):
    """1ワーカーが担当するURLチャンクをスクレイピングする。"""
    # 各スレッドで新しいDB接続を使う
    connections.close_all()

    driver = create_chrome_driver()
    success = 0
    errors = 0
    skipped = 0
    consecutive_errors = 0

    try:
        for i, (url, race_id) in enumerate(chunk):
            # リクエスト間隔（並列でもサイト負荷を抑える）
            time.sleep(1.5 + random.random())

            # 連続エラーが多い場合は長めに待機
            if consecutive_errors >= 5:
                logger.warning(f"W{worker_id} 連続エラー{consecutive_errors}回 → 30秒待機")
                time.sleep(30)
                consecutive_errors = 0

            try:
                base_df, html_content, base_flg = get_data(url, race_id, driver)
                result_df, kaisai_date, result_flg = get_result(url, race_id, "")

                if html_content in ("skip", "error"):
                    skipped += 1
                    consecutive_errors = 0
                    continue

                if len(base_df) != len(result_df):
                    skipped += 1
                    consecutive_errors = 0
                    continue

                insert_base_db(base_df, USERNAME)
                insert_result_db(result_df, USERNAME)

                if base_flg:
                    try:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, "base")
                    except Exception:
                        pass
                if result_flg:
                    try:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, "odds")
                    except Exception:
                        pass

                success += 1
                consecutive_errors = 0
            except Exception as e:
                errors += 1
                consecutive_errors += 1
                if errors <= 5:
                    logger.warning(f"W{worker_id} レース {race_id} エラー: {e}")
                continue

            if (i + 1) % 50 == 0:
                logger.info(f"W{worker_id}: {i+1}/{len(chunk)} (ok:{success} err:{errors} skip:{skipped})")

    finally:
        driver.quit()
        connections.close_all()

    return {"worker": worker_id, "success": success, "errors": errors, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description="並列base+resultスクレイピング")
    parser.add_argument('--workers', type=int, default=4, help='並列ワーカー数')
    parser.add_argument('--year', type=int, default=None, help='特定年度のみ')
    args = parser.parse_args()

    logger.info(f"==== 並列スクレイピング開始 (workers={args.workers}) ====")

    pending = get_pending_urls(year=args.year)
    total = len(pending)
    logger.info(f"未取得レース: {total} 件")

    if total == 0:
        logger.info("全レース取得済み")
        return

    # チャンク分割
    chunk_size = (total + args.workers - 1) // args.workers
    chunks = [pending[i:i + chunk_size] for i in range(0, total, chunk_size)]
    logger.info(f"チャンク: {len(chunks)} x ~{chunk_size} レース")

    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="scraper") as executor:
        futures = {
            executor.submit(scrape_chunk, chunk, i): i
            for i, chunk in enumerate(chunks)
        }

        for future in as_completed(futures):
            worker_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"W{worker_id} 完了: {result}")
            except Exception as e:
                logger.error(f"W{worker_id} 致命的エラー: {e}")

    elapsed = time.time() - start_time
    total_success = sum(r["success"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)

    logger.info(f"==== 完了 ({elapsed/60:.1f}分) ====")
    logger.info(f"  成功: {total_success} エラー: {total_errors} スキップ: {total_skipped}")
    logger.info(f"  Base: {BaseData.objects.count()} Result: {ResultData.objects.count()}")


if __name__ == '__main__':
    main()
