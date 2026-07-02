#!/usr/bin/env python3
"""
@file    backfill_last_3f.py
@brief   t_result_info の last_3f / margin 欠落レースを補完する
@version 1.0.0  2026-04-10  新規作成

対象: t_result_info.last_3f IS NULL のレース (3,990レース、2021-2022と2024-2025の一部)

戦略:
  1. 欠損レースのrace_id一覧を取得
  2. 各レースの result URL にurllibでアクセス
  3. 着順テーブルから (horse_number, 後3F, 着差) を抽出
  4. t_result_info を race_id + horse_number で UPDATE

使用方法:
    cd /home/dickey/デスクトップ/01_開発/02_dickey/03_keiba
    source venv/bin/activate
    nohup python scripts/backfill_last_3f.py > /tmp/backfill_last_3f.log 2>&1 &
    tail -f /tmp/backfill_last_3f.log
"""

import os
import sys
import logging
import time
import random
from io import StringIO
from urllib import request, error as urllib_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pandas as pd
from bs4 import BeautifulSoup
import psycopg2

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_ERRORS = 10

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def fetch_html(url: str) -> str | None:
    """urllib でHTMLを取得。"""
    req = request.Request(url, headers={'User-Agent': random.choice(USER_AGENTS)})
    try:
        response = request.urlopen(req, timeout=20)
        return response.read().decode('EUC-JP', errors='ignore')
    except urllib_error.HTTPError as e:
        logger.warning(f'HTTP {e.code}: {url}')
        return None
    except Exception as e:
        logger.warning(f'fetch失敗: {url} - {type(e).__name__}')
        return None


def parse_race_result(html: str):
    """resultページから (horse_number, last_3f, margin) のリストを返す。"""
    try:
        tables = pd.read_html(StringIO(html))
    except Exception:
        return None

    if not tables:
        return None

    main_df = pd.DataFrame(tables[0])

    # 必要カラム確認
    if '馬 番' not in main_df.columns:
        return None

    # 数値化できる行のみ（着順NaNを除外）
    main_df = main_df[pd.to_numeric(main_df['着 順'], errors='coerce').notna()].copy()
    if len(main_df) == 0:
        return None

    last_3f_col = main_df['後3F'] if '後3F' in main_df.columns else None
    margin_col = main_df['着差'] if '着差' in main_df.columns else None

    results = []
    for idx, row in main_df.iterrows():
        horse_number = str(row['馬 番']).strip()
        last_3f = str(last_3f_col.iloc[list(main_df.index).index(idx)]).strip() if last_3f_col is not None else None
        margin = str(margin_col.iloc[list(main_df.index).index(idx)]).strip() if margin_col is not None else None
        if last_3f in ('nan', 'NaN', ''):
            last_3f = None
        if margin in ('nan', 'NaN', ''):
            margin = None
        results.append((horse_number, last_3f, margin))

    return results


def main():
    conn = psycopg2.connect('dbname=keiba_db user=keiba_user password=KeibaDB@2026 host=localhost port=5432')
    cur = conn.cursor()

    # 欠損レース一覧
    cur.execute("""
        SELECT DISTINCT race_id
        FROM t_result_info
        WHERE last_3f IS NULL
        ORDER BY race_id
    """)
    race_ids = [r[0] for r in cur.fetchall()]

    logger.info(f'対象レース: {len(race_ids)}件')

    success = failed = updated_rows = 0
    consecutive_errors = 0

    for i, race_id in enumerate(race_ids):
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.error(f'連続エラー{consecutive_errors}回 → 強制停止')
            break

        try:
            url = f'https://race.netkeiba.com/race/result.html?race_id={race_id}'
            time.sleep(random.uniform(2, 5))
            html = fetch_html(url)
            if not html:
                failed += 1
                consecutive_errors += 1
                continue

            results = parse_race_result(html)
            if not results:
                failed += 1
                consecutive_errors += 1
                logger.warning(f'{race_id}: パース失敗')
                continue

            # UPDATE
            cnt = 0
            for horse_number, last_3f, margin in results:
                if last_3f is None and margin is None:
                    continue
                cur.execute("""
                    UPDATE t_result_info
                    SET last_3f = COALESCE(%s, last_3f),
                        margin = COALESCE(%s, margin)
                    WHERE race_id = %s AND horse_number = %s
                """, (last_3f, margin, race_id, horse_number))
                cnt += cur.rowcount
            conn.commit()

            success += 1
            updated_rows += cnt
            consecutive_errors = 0

        except Exception as e:
            failed += 1
            consecutive_errors += 1
            logger.warning(f'{race_id}: {type(e).__name__}: {str(e)[:100]}')
            conn.rollback()

        if (i + 1) % 50 == 0:
            long_wait = random.uniform(30, 60)
            logger.info(f'[{i+1}/{len(race_ids)}] ok:{success} fail:{failed} updated:{updated_rows} → {long_wait:.0f}秒休憩')
            time.sleep(long_wait)
        elif (i + 1) % 10 == 0:
            logger.info(f'[{i+1}/{len(race_ids)}] ok:{success} fail:{failed} updated:{updated_rows}')

    logger.info(f'Done: ok={success} fail={failed} updated_rows={updated_rows}')
    conn.close()


if __name__ == '__main__':
    main()
