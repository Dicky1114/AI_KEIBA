#!/usr/bin/env python3
"""
@file    scrape_pending.py
@brief   未取得レース (URLMst - t_base_info) を全件スクレイピングする
@version 1.2.0  2026-03-30  result()のタイムアウト修正 + venue/月フィルタ追加

使用方法:
    cd /home/dickey/デスクトップ/01_開発/02_dickey/03_keiba
    source venv/bin/activate
    nohup python scripts/scrape_pending.py > /tmp/scrape_pending.log 2>&1 &
    tail -f /tmp/scrape_pending.log
"""

import os
import sys
import logging
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from django.conf import settings
from django.db import transaction
from app_folder.models import URLMst, CreateRaceIDsView
from app_folder.services.get_base import get_data
from app_folder.services.get_result import result as get_result
from app_folder.services.insert_db import insert_base_db, insert_result_db
from app_folder.utils.driver import Driver
from app_folder.services.tasks import (
    change_user_agent, name_change, ensure_media_dirs,
    maybe_zip, maybe_unzip,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

BATCH_USER = "batch_scraper"
LOG_INTERVAL = 50

# JRA会場コード → 開催月マッピング (開催されない月はスキップ)
# 01=札幌 02=函館 03=福島 04=新潟 05=東京 06=中山 07=中京 08=京都 09=阪神 10=小倉
VENUE_ACTIVE_MONTHS = {
    '01': {6, 7, 8, 9},           # 札幌: 6-9月
    '02': {6, 7, 8},               # 函館: 6-8月
    '03': {4, 5, 10, 11},          # 福島: 4-5, 10-11月
    '04': {6, 7, 8, 10},           # 新潟: 6-8, 10月
    '05': {4, 5, 6, 10, 11},       # 東京: 4-6, 10-11月
    '06': {1, 2, 3, 9, 10, 11, 12},# 中山: 1-3, 9-12月
    '07': {1, 2, 3, 11, 12},       # 中京: 1-3, 11-12月
    '08': {3, 4, 5, 10, 11, 12},   # 京都: 3-5, 10-12月
    '09': {2, 3, 4, 11, 12},       # 阪神: 2-4, 11-12月
    '10': {1, 2, 8, 9},            # 小倉: 1-2, 8-9月
}


def is_valid_race(race_id: str) -> bool:
    """
    race_id (12文字) からレース開催の妥当性を判定する。
    YYYY VV KK DD RR の形式。
    - KK=kai: 01 または 02 のみ有効 (JRA実績での上限)
    """
    if len(race_id) != 12:
        return False
    kai = race_id[6:8]
    # kai=01,02のみ有効 (03以上はURLMstに誤生成されたID)
    return kai in {'01', '02'}


def has_cached_files(race_id: str) -> bool:
    """base と odds の両方のキャッシュHTMLが存在するか確認"""
    base_path = os.path.join(settings.MEDIA_ROOT, 'base')
    odds_path = os.path.join(settings.MEDIA_ROOT, 'odds')
    base_pattern = os.path.join(base_path, f"*{race_id}*.html")
    odds_pattern = os.path.join(odds_path, f"*{race_id}*.html")
    import glob as glob_mod
    return bool(glob_mod.glob(base_pattern)) and bool(glob_mod.glob(odds_pattern))


def main():
    ensure_media_dirs()

    # t_base_infoにないレースを取得
    pending_qs = CreateRaceIDsView.objects.exclude(
        race_id__in=["202404030612", "202408060108"]
    ).order_by("race_id").values_list("url", "race_id")

    all_pending = list(pending_qs)
    total_all = len(all_pending)

    # venue/月フィルタ + キャッシュ済みのみ処理
    pending_list = [
        (url, rid) for url, rid in all_pending
        if is_valid_race(rid) and has_cached_files(rid)
    ]
    filtered_out = total_all - len(pending_list)

    logger.info(f"=== 未取得レース: {total_all}件 (無効race_idを{filtered_out}件除外 → {len(pending_list)}件) ===")

    if not pending_list:
        logger.info("対象レースなし。終了。")
        return

    driver = Driver()
    zip_folder = settings.MEDIA_ROOT
    current_year = None
    processed = 0
    skipped = 0
    errors = 0
    start_time = time.time()

    try:
        for i, (url, race_id) in enumerate(pending_list):
            year = race_id[:4]

            if current_year is None:
                current_year = year
                maybe_unzip("base", year=year)
                maybe_unzip("odds", year=year)
            elif year != current_year:
                maybe_zip("base")
                maybe_zip("odds")
                current_year = year
                maybe_unzip("base", year=year)
                maybe_unzip("odds", year=year)

            with transaction.atomic():
                try:
                    base_df, html_content, base_flg = get_data(url, race_id, driver)
                    result_df, kaisai_date, result_flg = get_result(url, race_id, "", driver)

                    if html_content in ("skip", "continue"):
                        transaction.set_rollback(True)
                        skipped += 1
                        continue
                    if html_content == "error":
                        transaction.set_rollback(True)
                        errors += 1
                        continue

                    if not hasattr(base_df, '__len__') or not hasattr(result_df, '__len__'):
                        transaction.set_rollback(True)
                        skipped += 1
                        continue

                    if len(base_df) == 0 or len(result_df) == 0:
                        transaction.set_rollback(True)
                        skipped += 1
                        continue

                    if len(base_df) != len(result_df):
                        transaction.set_rollback(True)
                        skipped += 1
                        continue

                    insert_base_db(base_df, BATCH_USER)
                    insert_result_db(result_df, BATCH_USER)

                    if base_flg:
                        name_change(kaisai_date, zip_folder, race_id, "base")
                    if result_flg:
                        name_change(kaisai_date, zip_folder, race_id, "odds")

                    processed += 1

                except Exception as e:
                    transaction.set_rollback(True)
                    errors += 1
                    if errors <= 30:
                        logger.warning(f"  エラー ({race_id}): {e}")
                    continue

            if (i + 1) % LOG_INTERVAL == 0 or i == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                total = len(pending_list)
                remaining_sec = (total - i - 1) / (max(i + 1, 1) / max(elapsed, 1)) if elapsed > 0 else 0
                logger.info(
                    f"  [{i+1}/{total}] 処理:{processed} スキップ:{skipped} エラー:{errors} "
                    f"速度:{rate:.1f}件/s 残り:{remaining_sec/60:.0f}分"
                )

        maybe_zip("base")
        maybe_zip("odds")

    except KeyboardInterrupt:
        logger.info("中断されました")
        maybe_zip("base")
        maybe_zip("odds")
    except Exception as e:
        logger.error(f"予期せぬエラー: {e}", exc_info=True)
    finally:
        driver.quit()

    elapsed = time.time() - start_time
    logger.info(
        f"=== 完了: 処理:{processed} スキップ:{skipped} エラー:{errors} "
        f"所要時間:{elapsed/60:.1f}分 ==="
    )


if __name__ == "__main__":
    main()
