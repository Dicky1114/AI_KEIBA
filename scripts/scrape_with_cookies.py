#!/usr/bin/env python3
"""
@file    scrape_with_cookies.py
@brief   undetected-chromedriver + Cookie warmup付きbase+resultスクレイピング
@version 3.1.0  2026-04-08  連続エラー10回で強制停止 + IPブロック検出

変更理由:
  m_urlに無効race_id（元日等）が大量登録されており、
  毎回全件試すためsys_errループが発生していた。
  statusカラムで管理することで、確認済みのnot_found/okを再試行しない。
  v3.1: 連続エラー10回でIPブロックと判断し強制停止する。
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
from django.utils import timezone
from app_folder.models import URLMst, BaseData
from app_folder.services.get_base import get_data
from app_folder.services.get_result import result as get_result
from app_folder.services.insert_db import insert_base_db, insert_result_db
from app_folder.utils.driver import Driver
from app_folder.utils.zip import name_change

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

USERNAME = "batch_scraper"
MAX_CONSECUTIVE_ERRORS = 10


def make_driver():
    """Driver() のエイリアス。後方互換のため残す。"""
    return Driver()


def check_ip_blocked(driver) -> bool:
    """netkeiba.comトップにアクセスしてIPブロックされているか確認する。"""
    try:
        import urllib.request
        req = urllib.request.Request(
            'https://race.netkeiba.com/',
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        # HTTP 200 かつ Content-Length > 0 ならOK
        content = resp.read()
        if len(content) < 100:
            logger.warning(f'IPブロック疑い: レスポンスが{len(content)}バイト')
            return True
        return False
    except urllib.error.HTTPError as e:
        logger.warning(f'IPブロック検出: HTTP {e.code}')
        return True
    except Exception as e:
        logger.warning(f'IPブロック確認失敗: {e}')
        return True


def update_status(race_id: str, status: str):
    """m_url.statusを更新する。"""
    URLMst.objects.filter(race_id=race_id).update(status=status, updated_at=timezone.now())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, default=None)
    parser.add_argument('--limit', type=int, default=0, help='最大処理数 (0=無制限)')
    args = parser.parse_args()

    # status='pending' のものだけ取得 (ok/not_found は除外)
    qs = URLMst.objects.filter(status='pending').order_by('race_date', 'race_id')
    if args.year:
        qs = qs.filter(race_id__startswith=str(args.year))

    pending = list(qs.values_list('url', 'race_id'))

    if args.limit > 0:
        pending = pending[:args.limit]

    logger.info(f'Pending: {len(pending)} races')
    if not pending:
        logger.info('pending=0 — 完了済みか未登録')
        return

    driver = make_driver()
    success = errors = skipped = restarts = 0
    consecutive_errors = 0

    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'base'), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'odds'), exist_ok=True)

    try:
        for i, (url, race_id) in enumerate(pending):
            # 連続エラー10回で強制停止
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                blocked = check_ip_blocked(driver)
                if blocked:
                    logger.error(f'連続エラー{consecutive_errors}回 + IPブロック検出 → 強制停止')
                else:
                    logger.error(f'連続エラー{consecutive_errors}回 → 強制停止（原因不明）')
                break

            try:
                base_df, html_content, base_flg = get_data(url, race_id, driver)

                # not_found: 存在しないrace_id → DBに記録してスキップ
                if html_content == 'not_found':
                    update_status(race_id, 'not_found')
                    skipped += 1
                    consecutive_errors = 0
                    continue

                # DataFrameとstringを安全に比較
                if isinstance(base_df, str) and base_df == 'sys_err':
                    errors += 1
                    consecutive_errors += 1
                    logger.warning(f'{race_id}: sys_err')
                    continue

                if html_content in ('sys_err', 'skip', 'error', 'continue'):
                    if html_content == 'sys_err':
                        errors += 1
                        consecutive_errors += 1
                    else:
                        skipped += 1
                        consecutive_errors = 0
                    continue

                result_df, kaisai_date, result_flg = get_result(url, race_id, '', driver)
                if len(base_df) != len(result_df):
                    skipped += 1
                    consecutive_errors = 0
                    continue

                insert_base_db(base_df, USERNAME)
                insert_result_db(result_df, USERNAME)

                if base_flg:
                    try:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, 'base')
                    except Exception:
                        pass
                if result_flg:
                    try:
                        name_change(kaisai_date, settings.MEDIA_ROOT, race_id, 'odds')
                    except Exception:
                        pass

                # 成功 → status を ok に更新
                update_status(race_id, 'ok')
                success += 1
                consecutive_errors = 0

            except Exception as e:
                errors += 1
                consecutive_errors += 1
                logger.warning(f'{race_id}: {type(e).__name__}: {str(e)[:80]}')
                if 'session' in str(e).lower() or 'chrome' in str(e).lower():
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(3)
                    driver = make_driver()
                    restarts += 1

            # Bot対策①: 1〜20秒ランダム待機（毎回）
            time.sleep(random.uniform(1, 20))

            # Bot対策②: 50件ごとに長めの休憩（60〜120秒）
            if (i + 1) % 50 == 0:
                long_wait = random.uniform(60, 120)
                logger.info(f'[Bot対策] {i+1}件完了 → {long_wait:.0f}秒休憩')
                time.sleep(long_wait)

            # Bot対策③: 200件ごとにChrome再起動（セッションリセット）
            if (i + 1) % 200 == 0:
                logger.info(f'[Bot対策] {i+1}件完了 → Chromeセッションリセット')
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(random.uniform(10, 20))
                driver = make_driver()
                restarts += 1
                consecutive_errors = 0

            if (i + 1) % 100 == 0:
                logger.info(f'Progress: {i+1}/{len(pending)} ok:{success} err:{errors} skip:{skipped} restart:{restarts}')
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    logger.info(f'Done: ok={success} err={errors} skip={skipped} restart={restarts}')
    logger.info(f'Base rows: {BaseData.objects.count()} / pending残: {URLMst.objects.filter(status="pending").count()}')


if __name__ == '__main__':
    main()
