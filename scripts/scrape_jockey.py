#!/usr/bin/env python3
"""
@file    scrape_jockey.py
@brief   騎手成績データをdb.netkeibaから取得
@version 1.0.0  2026-04-10  新規作成

t_base_infoに登録済みの全騎手のjockey_urlから:
  - /?pid=jockey_detail&id={id}&page=N → t_jockey_info（過去成績）

戦略:
  1. t_base_info から jockey_id 一覧を取得（t_jockey_info 未登録のみ）
  2. 各騎手のページ1〜最終ページまで巡回
  3. 5年前より古いデータは打ち切り（既存get_jockey.pyと同じロジック）
  4. insert_jockey_db で DB UPDATE/INSERT

使用方法:
    cd /home/dickey/デスクトップ/01_開発/02_dickey/03_keiba
    source venv/bin/activate
    nohup python scripts/scrape_jockey.py > /tmp/scrape_jockey.log 2>&1 &
    tail -f /tmp/scrape_jockey.log
"""

import os
import sys
import logging
import time
import random
import datetime
from io import StringIO
from urllib import request, error as urllib_error
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

import pandas as pd
from bs4 import BeautifulSoup
from django.conf import settings
from app_folder.models import JockeyData
from app_folder.services.insert_db import insert_jockey_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

USERNAME = "batch_scraper"
MAX_CONSECUTIVE_ERRORS = 10
COLUMNS_TO_DROP = ['映 像']


def fetch_html(url: str) -> bytes | None:
    """HTMLを生バイトで取得。"""
    req = request.Request(url, headers=settings.HEADERS)
    try:
        response = request.urlopen(req, timeout=20)
        return response.read()
    except Exception as e:
        logger.warning(f'fetch失敗: {url} - {type(e).__name__}')
        return None


def get_last_page(html_bytes: bytes) -> int:
    """最終ページ番号を取得。"""
    soup = BeautifulSoup(html_bytes, 'html.parser')
    a_tag = soup.find('a', title="最後")
    if not a_tag:
        return 2
    url = a_tag.get('href', '')
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    page = qs.get('page', ['2'])[0]
    try:
        return int(page)
    except ValueError:
        return 2


def scrape_jockey_page(jockey_url_base: str, page: int) -> pd.DataFrame | None:
    """1ページ分のデータを取得。"""
    url = f'{jockey_url_base}{page}'
    html_bytes = fetch_html(url)
    if not html_bytes:
        return None

    try:
        tables = pd.read_html(StringIO(html_bytes.decode('EUC-JP', errors='ignore')))
    except Exception:
        return None

    if not tables:
        return None

    df = pd.DataFrame(tables[0][:])
    try:
        df = df.drop(columns=COLUMNS_TO_DROP)
    except Exception:
        pass
    return df


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    import psycopg2
    conn = psycopg2.connect('dbname=keiba_db user=keiba_user password=KeibaDB@2026 host=localhost port=5432')
    cur = conn.cursor()

    # t_base_info から jockey_id 一覧（t_jockey_info 未登録のみ）
    cur.execute("""
        SELECT DISTINCT jockey_url, jockey_name
        FROM t_base_info
        WHERE jockey_url IS NOT NULL AND jockey_url != ''
        ORDER BY jockey_url
    """)
    all_jockeys = cur.fetchall()

    cur.execute("SELECT DISTINCT jockey_id FROM t_jockey_info")
    registered_ids = {r[0] for r in cur.fetchall()}
    conn.close()

    # jockey_id抽出と未登録フィルタ
    jockeys = []
    for url, name in all_jockeys:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        jid = qs.get('id', [None])[0]
        if not jid or jid in registered_ids:
            continue
        jockeys.append((jid, name, url))

    if args.limit > 0:
        jockeys = jockeys[:args.limit]

    logger.info(f'対象騎手: {len(jockeys)}名 (t_jockey_info未登録)')
    if not jockeys:
        logger.info('全騎手取得済み')
        return

    cutoff_year = str(datetime.datetime.today().year - 5)
    success = errors = 0
    consecutive_errors = 0

    for i, (jockey_id, jockey_name, jockey_url) in enumerate(jockeys):
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.error(f'連続エラー{consecutive_errors}回 → 強制停止')
            break

        try:
            jockey_url_base = jockey_url[:-1]  # 末尾の "1" を外す → "&page="

            # 最初のページ取得して最終ページ番号を調べる
            time.sleep(random.uniform(2, 4))
            first_html = fetch_html(jockey_url)
            if not first_html:
                errors += 1
                consecutive_errors += 1
                continue

            last_page = get_last_page(first_html)

            # 全ページを巡回
            for page in range(1, last_page):
                time.sleep(random.uniform(1.5, 3))
                df = scrape_jockey_page(jockey_url_base, page)
                if df is None or df.empty or '日付' not in df.columns:
                    break

                # 5年カットオフ
                try:
                    latest_date = datetime.datetime.strptime(
                        df.sort_values(by='日付', ascending=False).iloc[0]['日付'], "%Y/%m/%d"
                    )
                    if latest_date.strftime('%Y-%m-%d')[:4] <= cutoff_year:
                        break
                except Exception:
                    break

                df['日付'] = df['日付'].astype(str).str.replace('/', '-', regex=False)
                df['レース名'] = df['レース名'].fillna('')
                df['new_flg']     = df['レース名'].str.contains('新馬').astype(int)
                df['win_1_flg']   = df['レース名'].str.contains('1勝').astype(int)
                df['win_2_flg']   = df['レース名'].str.contains('2勝').astype(int)
                df['win_3_flg']   = df['レース名'].str.contains('3勝').astype(int)
                df['not_win_flg'] = df['レース名'].str.contains('未勝利').astype(int)
                df['g3_flg']      = df['レース名'].str.contains('GⅢ').astype(int)
                df['g2_flg']      = df['レース名'].str.contains('GⅡ').astype(int)
                df['g1_flg']      = df['レース名'].str.contains('GI').astype(int)
                df['l_flg']       = df['レース名'].str.contains(r'\(L\)').astype(int)
                df['op_flg']      = df['レース名'].str.contains(r'\(OP\)').astype(int)
                df['jockey_id']   = jockey_id
                df['jockey_name'] = jockey_name

                df.rename(columns=settings.NEW_JOCKEY_COL, inplace=True)
                if 'race' in df.columns:
                    df['race'] = df['race'].apply(lambda x: str(x).strip())
                df = df.dropna(subset=['race_date'])

                insert_jockey_db(df, USERNAME)

            success += 1
            consecutive_errors = 0

        except Exception as e:
            errors += 1
            consecutive_errors += 1
            logger.warning(f'{jockey_name} ({jockey_id}): {type(e).__name__}: {str(e)[:100]}')

        if (i + 1) % 10 == 0:
            long_wait = random.uniform(20, 40)
            logger.info(f'[{i+1}/{len(jockeys)}] ok:{success} err:{errors} → {long_wait:.0f}秒休憩')
            time.sleep(long_wait)
        elif (i + 1) % 3 == 0:
            logger.info(f'[{i+1}/{len(jockeys)}] ok:{success} err:{errors}')

    logger.info(f'Done: ok={success} err={errors}')
    logger.info(f't_jockey_info: {JockeyData.objects.count()} rows')


if __name__ == '__main__':
    main()
