#!/usr/bin/env python3
"""
@file    scrape_horse_blood_v3.py
@brief   馬の過去成績+血統データをdb.netkeibaから取得（安全版）
@version 3.0.0  2026-04-11  IPブロック防止策を全面強化

v2からの改善点（すべて安全重視）:
  1. 単一ワーカー実行（並列化廃止）
  2. 最新race_date順（新しい馬から先に処理）
  3. sleep延長: 3-7s + 3-7s (平均10s/馬)
  4. 100頭ごとのクールダウン 60-120秒
  5. User-Agent 5種類ランダムローテ
  6. Referer チェーン（前回URL → 現在URL）
  7. IPブロック即時検知（HTTP 400検知で自動停止）
  8. 時間制限（1時間あたり最大300馬）
  9. 連続エラー上限 30 (ネットワーク障害のみカウント)

使用方法:
    cd /home/dickey/デスクトップ/01_開発/02_dickey/03_keiba
    source venv/bin/activate
    nohup python scripts/scrape_horse_blood_v3.py > /tmp/scrape_horse_v3.log 2>&1 &
    tail -f /tmp/scrape_horse_v3.log
"""

import os
import sys
import logging
import time
import random
import datetime
from urllib import request, error as urllib_error
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

import pandas as pd
from django.conf import settings
import psycopg2
from psycopg2.extras import execute_values

USERNAME = "batch_scraper_v3"
MAX_CONSECUTIVE_NET_ERRORS = 30
MAX_PER_HOUR = 350  # 時間あたり最大馬数
DB_DSN = 'dbname=keiba_db user=keiba_user password=KeibaDB@2026 host=localhost port=5432'

# HTTPステータス種別
HTTP_NOT_FOUND = 'NOT_FOUND'   # 400/404 = 個別馬の問題
HTTP_BLOCKED = 'BLOCKED'       # 連続400 = IPブロック疑い
HTTP_ERROR = 'HTTP_ERROR'      # ネットワーク障害
NO_DATA = 'NO_DATA'            # HTMLは取れたがパース対象なし

# ブラウザ偽装用User-Agent
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

HORSE_FIELDS = [
    'horse_id', 'horse_name', 'race_date', 'race_place', 'weather', 'race_name',
    'horse_number', 'count', 'frame', 'odds', 'popularity', 'rank',
    'jockey', 'weight', 'distance', 'track_condition', 'time', 'time_diff',
    'position', 'pace', 'up', 'body_weight', 'winner', 'prize',
    'new_flg', 'win_1_flg', 'win_2_flg', 'win_3_flg', 'not_win_flg',
    'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg',
    'created_at', 'updated_at', 'created_user', 'updated_user',
]

BLOOD_FIELDS = [
    'horse_id', 'horse_name',
    'sire_1_male', 'sire_1_female',
    'sire_2_1_male', 'sire_2_1_female',
    'sire_2_2_male', 'sire_2_2_female',
    'created_at', 'updated_at', 'created_user', 'updated_user',
]


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


def build_headers(referer: str | None = None) -> dict:
    """ブラウザ偽装ヘッダーを生成。"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'identity',  # 明示的に圧縮しない（urllibが解凍できないため）
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin' if referer else 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    if referer:
        headers['Referer'] = referer
    return headers


def fetch_html(url: str, referer: str | None = None):
    """
    HTMLを取得。
    成功時: str (HTML)
    400/404: HTTP_NOT_FOUND
    その他失敗: HTTP_ERROR
    """
    req = request.Request(url, headers=build_headers(referer))
    try:
        response = request.urlopen(req, timeout=20)
        return response.read().decode('EUC-JP', errors='ignore')
    except urllib_error.HTTPError as e:
        if e.code in (400, 404):
            return HTTP_NOT_FOUND
        return HTTP_ERROR
    except Exception:
        return HTTP_ERROR


def check_ip_not_blocked() -> bool:
    """IPブロック確認（ルートパスで200が返るかチェック）。"""
    try:
        req = request.Request('https://db.netkeiba.com/', headers=build_headers())
        resp = request.urlopen(req, timeout=10)
        return resp.status == 200
    except urllib_error.HTTPError as e:
        return e.code != 400
    except Exception:
        return False


def extract_name(td):
    """血統テーブルのtdから馬名のみ抽出する。"""
    a = td.find('a')
    if a:
        return a.text.strip().split('\n')[0].strip()
    return td.text.strip().split('\n')[0].strip()


def fetch_horse_history(horse_id: str, referer: str | None = None):
    """馬の過去成績を取得する。"""
    url = f'https://db.netkeiba.com/horse/result/{horse_id}/'
    html = fetch_html(url, referer)
    if html in (HTTP_NOT_FOUND, HTTP_ERROR):
        return html, url
    if not html:
        return HTTP_ERROR, url

    try:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='db_h_race_results')
        if not table:
            return NO_DATA, url

        ths = table.find('tr').find_all('th')
        header = [th.text.strip().replace('\n', '') for th in ths]
        col_idx = {name: i for i, name in enumerate(header)}

        required = ['日付', '開催', '天気', 'レース名', '頭数', '枠番', '馬番',
                    'オッズ', '人気', '着順', '騎手', '斤量', '距離', '馬場',
                    'タイム', '着差', '通過', 'ペース', '上り', '馬体重', '勝ち馬(2着馬)', '賞金']
        for req in required:
            if req not in col_idx:
                return NO_DATA, url

        rows_data = []
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if len(tds) < len(header):
                continue
            row = {
                '日付': tds[col_idx['日付']].text.strip().replace('/', '-'),
                '開催': tds[col_idx['開催']].text.strip(),
                '天 気': tds[col_idx['天気']].text.strip(),
                'レース名': tds[col_idx['レース名']].text.strip(),
                '頭 数': tds[col_idx['頭数']].text.strip(),
                '枠 番': tds[col_idx['枠番']].text.strip(),
                '馬 番': tds[col_idx['馬番']].text.strip(),
                'オ ッ ズ': tds[col_idx['オッズ']].text.strip(),
                '人 気': tds[col_idx['人気']].text.strip(),
                '着 順': tds[col_idx['着順']].text.strip(),
                '騎手': tds[col_idx['騎手']].text.strip(),
                '斤 量': tds[col_idx['斤量']].text.strip(),
                '距離': tds[col_idx['距離']].text.strip(),
                '馬 場': tds[col_idx['馬場']].text.strip(),
                'タイム': tds[col_idx['タイム']].text.strip(),
                '着差': tds[col_idx['着差']].text.strip(),
                '通過': tds[col_idx['通過']].text.strip(),
                'ペース': tds[col_idx['ペース']].text.strip(),
                '上り': tds[col_idx['上り']].text.strip(),
                '馬体重': tds[col_idx['馬体重']].text.strip(),
                '勝ち馬 (2着馬)': tds[col_idx['勝ち馬(2着馬)']].text.strip(),
                '賞金': tds[col_idx['賞金']].text.strip(),
            }
            rows_data.append(row)

        if not rows_data:
            return NO_DATA, url

        perf_df = pd.DataFrame(rows_data)

        for flag, kw in [('new_flg', '新馬'), ('win_1_flg', '1勝'), ('win_2_flg', '2勝'),
                         ('win_3_flg', '3勝'), ('not_win_flg', '未勝利')]:
            perf_df[flag] = perf_df['レース名'].str.contains(kw, na=False).astype(bool)
        perf_df['g3_flg'] = perf_df['レース名'].str.contains('GⅢ', na=False).astype(bool)
        perf_df['g2_flg'] = perf_df['レース名'].str.contains('GⅡ', na=False).astype(bool)
        perf_df['g1_flg'] = perf_df['レース名'].str.contains('GI', na=False).astype(bool)
        perf_df['l_flg'] = perf_df['レース名'].str.contains(r'\(L\)', na=False).astype(bool)
        perf_df['op_flg'] = perf_df['レース名'].str.contains(r'\(OP\)', na=False).astype(bool)

        perf_df.rename(columns=settings.NEW_HORSE_COL, inplace=True)
        return perf_df, url
    except Exception:
        return NO_DATA, url


def fetch_blood(horse_id: str, referer: str | None = None):
    """血統データを取得する。"""
    url = f'https://db.netkeiba.com/horse/ped/{horse_id}/'
    html = fetch_html(url, referer)
    if html in (HTTP_NOT_FOUND, HTTP_ERROR) or not html:
        return None, url

    try:
        soup = BeautifulSoup(html, 'html.parser')
        blood = soup.find('table', class_='blood_table')
        if not blood:
            return None, url

        rows = blood.find_all('tr')
        if len(rows) < 32:
            return None, url

        return {
            'sire_1_male': extract_name(rows[0].find_all('td')[0]),
            'sire_1_female': extract_name(rows[16].find_all('td')[0]),
            'sire_2_1_male': extract_name(rows[0].find_all('td')[1]),
            'sire_2_1_female': extract_name(rows[8].find_all('td')[0]),
            'sire_2_2_male': extract_name(rows[16].find_all('td')[1]),
            'sire_2_2_female': extract_name(rows[24].find_all('td')[0]),
        }, url
    except Exception:
        return None, url


def df_to_horse_rows(df: pd.DataFrame, now) -> list:
    """DataFrame → bulk insert 用タプルリスト。"""
    rows = []
    for _, r in df.iterrows():
        try:
            rows.append((
                r.get('horse_id'), r.get('horse_name'), r.get('race_date'),
                r.get('race_place'), r.get('weather'), r.get('race_name'),
                r.get('horse_number'), r.get('count'), r.get('frame'),
                r.get('odds'), r.get('popularity'), r.get('rank'),
                r.get('jockey'), r.get('weight'), r.get('distance'),
                r.get('track_condition'), r.get('time'), r.get('time_diff'),
                r.get('position'), r.get('pace'), r.get('up'),
                r.get('body_weight'), r.get('winner'), r.get('prize'),
                bool(r.get('new_flg', False)), bool(r.get('win_1_flg', False)),
                bool(r.get('win_2_flg', False)), bool(r.get('win_3_flg', False)),
                bool(r.get('not_win_flg', False)), bool(r.get('g3_flg', False)),
                bool(r.get('g2_flg', False)), bool(r.get('g1_flg', False)),
                bool(r.get('l_flg', False)), bool(r.get('op_flg', False)),
                now, now, USERNAME, USERNAME,
            ))
        except Exception:
            continue
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    # 起動前にIPブロック確認
    logger.info('IPブロック事前チェック中...')
    if not check_ip_not_blocked():
        logger.error('IPブロック検出 → 起動中止')
        return
    logger.info('IPブロックなし、起動します')

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # 最新のrace_dateで出走した馬から優先処理
    # 同一horse_idは最新のrace_dateを使用
    cur.execute("""
        WITH horse_latest AS (
            SELECT DISTINCT ON (SPLIT_PART(horse_url, '/', 5))
                SPLIT_PART(horse_url, '/', 5) as horse_id,
                horse_name,
                race_date
            FROM t_base_info
            WHERE horse_url IS NOT NULL AND horse_url != ''
            ORDER BY SPLIT_PART(horse_url, '/', 5), race_date DESC
        )
        SELECT horse_id, horse_name
        FROM horse_latest
        WHERE horse_id NOT IN (SELECT DISTINCT horse_id FROM t_horse_info)
        ORDER BY race_date DESC, horse_id
    """)
    horses = cur.fetchall()

    if args.limit > 0:
        horses = horses[:args.limit]

    logger.info(f'対象馬: {len(horses)}頭 (最新race_date順)')

    if not horses:
        logger.info('処理対象なし')
        conn.close()
        return

    success_hist = success_blood = errors = skipped = not_found = 0
    consecutive_net_errors = 0
    consecutive_not_found = 0  # ブロック疑い検出用
    total_inserted = 0

    hour_start = time.time()
    hour_count = 0

    # 最初のRefererは人がGoogleから辿り着いた体でトップページ設定
    prev_url = 'https://db.netkeiba.com/'

    for i, (horse_id, horse_name) in enumerate(horses):
        # 連続ネットワークエラー上限
        if consecutive_net_errors >= MAX_CONSECUTIVE_NET_ERRORS:
            logger.error(f'連続ネットエラー{consecutive_net_errors}回 → 強制停止')
            break

        # 連続NotFound = IPブロック疑い
        if consecutive_not_found >= 15:
            logger.error(f'連続NotFound{consecutive_not_found}回 → IPブロック疑いで停止')
            break

        # 時間あたり上限チェック
        elapsed = time.time() - hour_start
        if elapsed < 3600 and hour_count >= MAX_PER_HOUR:
            wait = 3600 - elapsed
            logger.info(f'時間上限({MAX_PER_HOUR}頭)到達、{wait:.0f}秒休憩')
            time.sleep(wait)
            hour_start = time.time()
            hour_count = 0
        elif elapsed >= 3600:
            hour_start = time.time()
            hour_count = 0

        try:
            # 過去成績取得
            time.sleep(random.uniform(3, 7))
            result, hist_url = fetch_horse_history(horse_id, referer=prev_url)
            prev_url = hist_url

            # 文字列ステータスの判定 (DataFrame は isinstance で判定)
            if isinstance(result, str):
                if result == HTTP_NOT_FOUND:
                    not_found += 1
                    consecutive_not_found += 1
                    consecutive_net_errors = 0
                    continue
                if result == NO_DATA:
                    skipped += 1
                    consecutive_not_found = 0
                    consecutive_net_errors = 0
                    continue
                if result == HTTP_ERROR:
                    errors += 1
                    consecutive_net_errors += 1
                    logger.warning(f'{horse_name} ({horse_id}): ネットワーク障害')
                    time.sleep(random.uniform(10, 20))
                    continue

            # DataFrame が返ってきた場合
            consecutive_not_found = 0
            perf_df = result
            if perf_df is not None and len(perf_df) > 0:
                perf_df['horse_id'] = horse_id
                perf_df['horse_name'] = horse_name
                perf_df = perf_df.drop_duplicates(subset=['horse_id', 'race_date'])

                now = datetime.datetime.now(datetime.timezone.utc)
                rows = df_to_horse_rows(perf_df, now)
                if rows:
                    cols = ','.join(f'"{f}"' for f in HORSE_FIELDS)
                    sql = f'INSERT INTO t_horse_info ({cols}) VALUES %s'
                    execute_values(cur, sql, rows, page_size=100)
                    conn.commit()
                    total_inserted += len(rows)

                success_hist += 1
            else:
                skipped += 1
                consecutive_net_errors = 0
                continue

            # 血統取得
            time.sleep(random.uniform(3, 7))
            blood, ped_url = fetch_blood(horse_id, referer=prev_url)
            prev_url = ped_url

            if blood:
                now = datetime.datetime.now(datetime.timezone.utc)
                blood_row = (
                    horse_id, horse_name,
                    blood['sire_1_male'], blood['sire_1_female'],
                    blood['sire_2_1_male'], blood['sire_2_1_female'],
                    blood['sire_2_2_male'], blood['sire_2_2_female'],
                    now, now, USERNAME, USERNAME,
                )
                cols = ','.join(f'"{f}"' for f in BLOOD_FIELDS)
                sql = f'INSERT INTO m_horse_blood ({cols}) VALUES %s'
                execute_values(cur, sql, [blood_row])
                conn.commit()
                success_blood += 1

            consecutive_net_errors = 0
            hour_count += 1

        except Exception as e:
            errors += 1
            consecutive_net_errors += 1
            logger.warning(f'{horse_name} ({horse_id}): {type(e).__name__}: {str(e)[:100]}')
            conn.rollback()

        # 100頭ごとに長めのクールダウン
        if (i + 1) % 100 == 0:
            long_wait = random.uniform(60, 120)
            logger.info(f'[{i+1}/{len(horses)}] hist:{success_hist} blood:{success_blood} skip:{skipped} notfound:{not_found} err:{errors} inserted:{total_inserted} → {long_wait:.0f}秒休憩')
            time.sleep(long_wait)
        elif (i + 1) % 20 == 0:
            logger.info(f'[{i+1}/{len(horses)}] hist:{success_hist} blood:{success_blood} skip:{skipped} notfound:{not_found} err:{errors} inserted:{total_inserted}')

    logger.info(f'Done: hist={success_hist} blood={success_blood} skip={skipped} notfound={not_found} err={errors} inserted={total_inserted}')
    conn.close()


if __name__ == '__main__':
    main()
