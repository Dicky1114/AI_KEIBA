#!/usr/bin/env python3
"""
@file    scrape_with_cookies.py
@brief   Cookie warmup付きbase+resultスクレイピング
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)

netkeiba.comはCookie無しのリクエストに400を返すため、
まずwww.netkeiba.comにアクセスしてCookieを取得してからレースページにアクセスする。
"""

import os
import sys
import logging
import time
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app_folder.models import URLMst, BaseData
from app_folder.services.get_base import get_data
from app_folder.services.get_result import result as get_result
from app_folder.services.insert_db import insert_base_db, insert_result_db
from app_folder.utils.zip import name_change

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

USERNAME = "batch_scraper"


def make_driver():
    """Bot検出回避設定付きChromeドライバーを作成し、Cookie warmupする。"""
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    ua = random.choice(getattr(settings, 'USER_AGENTS', [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
    ]))
    opts.add_argument(f'--user-agent={ua}')
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)

    d = webdriver.Chrome(options=opts)
    d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })

    # Cookie warmup
    d.get('https://www.netkeiba.com/')
    time.sleep(2)
    logger.info(f'Cookie warmup完了: {len(d.get_cookies())} cookies')
    return d


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, default=None)
    parser.add_argument('--limit', type=int, default=0, help='最大処理数 (0=無制限)')
    args = parser.parse_args()

    existing = set(BaseData.objects.values_list('race_id', flat=True).distinct())
    qs = URLMst.objects.order_by('race_date', 'race_id')
    if args.year:
        qs = qs.filter(race_id__startswith=str(args.year))
    pending = [(u.url, u.race_id) for u in qs if u.race_id not in existing]

    if args.limit > 0:
        pending = pending[:args.limit]

    logger.info(f'Pending: {len(pending)} races')
    if not pending:
        return

    driver = make_driver()
    success = errors = skipped = restarts = 0
    consecutive_errors = 0

    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'base'), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'odds'), exist_ok=True)

    try:
        for i, (url, race_id) in enumerate(pending):
            # 連続エラー時はChrome再起動
            if consecutive_errors >= 10:
                logger.warning(f'連続エラー{consecutive_errors}回 → Chrome再起動')
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(5)
                driver = make_driver()
                restarts += 1
                consecutive_errors = 0

            try:
                base_df, html_content, base_flg = get_data(url, race_id, driver)

                if base_df == 'sys_err' or html_content == 'sys_err':
                    errors += 1
                    consecutive_errors += 1
                    if consecutive_errors <= 3:
                        logger.warning(f'{race_id}: sys_err')
                    continue

                if html_content in ('skip', 'error', 'continue'):
                    skipped += 1
                    consecutive_errors = 0
                    continue

                result_df, kaisai_date, result_flg = get_result(url, race_id, '')
                if len(base_df) != len(result_df):
                    skipped += 1
                    consecutive_errors = 0
                    continue

                insert_base_db(base_df, USERNAME)
                insert_result_db(result_df, USERNAME)

                if base_flg:
                    try:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, 'base')
                    except:
                        pass
                if result_flg:
                    try:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, 'odds')
                    except:
                        pass

                success += 1
                consecutive_errors = 0
            except Exception as e:
                errors += 1
                consecutive_errors += 1
                if errors <= 10:
                    logger.warning(f'{race_id}: {type(e).__name__}: {str(e)[:80]}')
                if 'session' in str(e).lower() or 'chrome' in str(e).lower():
                    try:
                        driver.quit()
                    except:
                        pass
                    time.sleep(3)
                    driver = make_driver()
                    restarts += 1
                    consecutive_errors = 0

            if (i + 1) % 100 == 0:
                logger.info(f'Progress: {i+1}/{len(pending)} ok:{success} err:{errors} skip:{skipped} restart:{restarts}')
    finally:
        try:
            driver.quit()
        except:
            pass

    logger.info(f'Done: ok={success} err={errors} skip={skipped} restart={restarts}')
    logger.info(f'Base: {BaseData.objects.count()} races: {BaseData.objects.values("race_id").distinct().count()}')


if __name__ == '__main__':
    main()
