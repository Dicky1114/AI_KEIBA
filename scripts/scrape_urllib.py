#!/usr/bin/env python3
"""
@file    scrape_urllib.py
@brief   urllib直接取得による軽量スクレイピング（Selenium不使用）
@version 4.0.0  2026-04-08  resultページをurllibで取得し既存パーサーを再利用

既存の get_data() / get_result() はキャッシュファイルがあればそこから読む。
本スクリプトは「resultページのHTMLをurllibで事前ダウンロードし、
baseキャッシュとしても保存する」ことで、既存パーサーをSeleniumなしで動かす。

戦略:
  1. result URL を urllib で取得 → media/odds/{race_id}.html に保存
  2. 同じHTMLを media/base/{race_id}.html にも保存（baseパーサー用）
  3. 既存の get_data() / get_result() を呼ぶ → キャッシュから読む
  4. ただしget_data()はshutuba形式のHTMLを期待するため、
     resultページからbase_dfを直接構築する独自パーサーを使用

使用方法:
    cd /home/dickey/デスクトップ/01_開発/02_dickey/03_keiba
    source venv/bin/activate
    nohup python scripts/scrape_urllib.py > /tmp/scrape_keiba.log 2>&1 &
    tail -f /tmp/scrape_keiba.log
"""

import os
import sys
import logging
import time
import random
import re
import datetime
from zoneinfo import ZoneInfo
from urllib import request, error as urllib_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone
from app_folder.models import URLMst, BaseData
from app_folder.services.insert_db import insert_base_db, insert_result_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

USERNAME = "batch_scraper"
MAX_CONSECUTIVE_ERRORS = 10
# ブロック対策パラメータ(main の引数で上書き可)
FETCH_MAX_RETRIES = 3          # 429/403/timeout 時の再試行回数
BACKOFF_BASE = 30             # 指数バックオフの基準秒(30,60,120...)
THROTTLE_CODES = (403, 429, 503)  # レート制限とみなすHTTPコード


def _decode(raw: bytes) -> str:
    # WHY: netkeibaは2026にEUC-JP→UTF-8へ移行済。宣言charsetを優先し、
    #      無ければutf-8で復号する(旧EUC-JP固定だと列名が文字化けしてパース失敗)。
    head = raw[:2000].decode('ascii', errors='ignore')
    m = re.search(r'charset=["\']?([\w-]+)', head, re.I)
    enc = (m.group(1) if m else 'utf-8')
    try:
        return raw.decode(enc, errors='ignore')
    except (LookupError, UnicodeDecodeError):
        return raw.decode('utf-8', errors='ignore')


def fetch_html(url: str) -> str | None:
    """urllib でHTMLを取得する。

    ブロック対策:
      - レート制限(403/429/503)/タイムアウトは指数バックオフ(30→60→120秒)で再試行。
      - 再試行を使い切ったら None を返し、呼び出し側のサーキットブレーカーに委ねる。
        (=叩き続けず、止まって待つ/再開できる設計)
    """
    for attempt in range(FETCH_MAX_RETRIES + 1):
        header = random.choice(settings.USER_AGENTS)
        req = request.Request(url, headers={'User-Agent': header})
        try:
            response = request.urlopen(req, timeout=20)
            return _decode(response.read())
        except urllib_error.HTTPError as e:
            if e.code in THROTTLE_CODES and attempt < FETCH_MAX_RETRIES:
                wait = BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 10)
                logger.warning(f'HTTP {e.code} (レート制限?) → {wait:.0f}秒バックオフ後に再試行 [{attempt+1}/{FETCH_MAX_RETRIES}] {url}')
                time.sleep(wait)
                continue
            logger.warning(f'HTTP {e.code}: {url}')
            return None
        except (urllib_error.URLError, TimeoutError) as e:
            if attempt < FETCH_MAX_RETRIES:
                wait = BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 10)
                logger.warning(f'通信エラー({type(e).__name__}) → {wait:.0f}秒後に再試行 [{attempt+1}/{FETCH_MAX_RETRIES}] {url}')
                time.sleep(wait)
                continue
            return None
        except Exception:
            return None
    return None


def check_ip_blocked() -> bool:
    """IPブロック確認。"""
    try:
        req = request.Request('https://race.netkeiba.com/',
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
        resp = request.urlopen(req, timeout=10)
        return len(resp.read()) < 100
    except Exception:
        return True


def update_status(race_id: str, status: str):
    URLMst.objects.filter(race_id=race_id).update(status=status, updated_at=timezone.now())


def parse_payouts(tables):
    """払戻金テーブルからresult用dictを返す。"""
    result = {}
    df1 = pd.DataFrame(tables[1])
    df2 = pd.DataFrame(tables[2])

    # 3連単 → positions
    try:
        value = df2.loc[df2[0] == '3連単', 1].values[0]
        split = [item for item in value.split(' ') if item]
        positions = []
        for i in range(0, len(split), 3):
            positions.append('>'.join(split[i:i+3]))
        result['positions'] = positions[0] if positions else ''
        result['positions_tie'] = positions[1] if len(positions) > 1 else ''
    except Exception:
        result['positions'] = ''
        result['positions_tie'] = ''

    # 複勝
    try:
        value = df1.loc[df1[0] == '複勝', 2].values[0]
        split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
        result['pay123_1'] = split[0]
        result['pay123_2'] = split[1]
        if len(split) == 2:
            result['pay123_3'] = ''
            result['pay123_tie'] = ''
        elif len(split) == 3:
            if '枠連' in df1[0].values:
                result['pay123_3'] = split[2]
                result['pay123_tie'] = ''
            else:
                result['pay123_3'] = ''
                result['pay123_tie'] = split[2]
        else:
            result['pay123_3'] = split[2]
            result['pay123_tie'] = split[3]
    except Exception:
        result.update({'pay123_1': '', 'pay123_2': '', 'pay123_3': '', 'pay123_tie': ''})

    # 単勝
    try:
        value = df1.loc[df1[0] == '単勝', 2].values[0]
        split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
        result['pay1'] = split[0]
        result['pay1_tie'] = split[1] if len(split) > 1 else ''
    except Exception:
        result.update({'pay1': '', 'pay1_tie': ''})

    # 馬単
    try:
        value = df2.loc[df2[0] == '馬単', 2].values[0]
        split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
        result['pay12_12'] = split[0]
        result['pay12_12_tie'] = split[1] if len(split) > 1 else ''
    except Exception:
        result.update({'pay12_12': '', 'pay12_12_tie': ''})

    # 馬連
    try:
        value = df1.loc[df1[0] == '馬連', 2].values[0]
        split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
        result['pay12_21'] = split[0]
        result['pay12_21_tie'] = split[1] if len(split) > 1 else ''
    except Exception:
        result.update({'pay12_21': '', 'pay12_21_tie': ''})

    # 3連単 (払戻)
    try:
        value = df2.loc[df2[0] == '3連単', 2].values[0]
        split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
        result['pay123_123'] = split[0]
        result['pay123_123_tie'] = split[1] if len(split) > 1 else ''
    except Exception:
        result.update({'pay123_123': '', 'pay123_123_tie': ''})

    # 3連複
    try:
        value = df2.loc[df2[0] == '3連複', 2].values[0]
        split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
        result['pay123_321'] = split[0]
        result['pay123_321_tie'] = split[1] if len(split) > 1 else ''
    except Exception:
        result.update({'pay123_321': '', 'pay123_321_tie': ''})

    # ワイド
    try:
        wide_rows = df2.loc[df2[0] == 'ワイド', 2]
        if wide_rows.empty:
            raise ValueError()
        value = wide_rows.values[0]
        split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
        result['pay123_12_1'] = split[0] if len(split) > 0 else ''
        result['pay123_12_2'] = split[1] if len(split) > 1 else ''
        result['pay123_12_3'] = split[2] if len(split) > 2 else ''
        result['pay123_12_4_tie'] = split[3] if len(split) > 3 else ''
        result['pay123_12_5_tie'] = split[4] if len(split) > 4 else ''
    except Exception:
        result.update({'pay123_12_1': '', 'pay123_12_2': '', 'pay123_12_3': '',
                       'pay123_12_4_tie': '', 'pay123_12_5_tie': ''})

    return result


def process_result_page(html_content: str, race_id: str):
    """resultページからbase_dfとresult_df(払戻金付き)の両方を構築する。"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # 開催日
    kaisai_date_str = None
    active_dd = soup.find('dd', class_='Active')
    if active_dd:
        a_tag = active_dd.find('a')
        if a_tag and 'href' in a_tag.attrs:
            for param in a_tag['href'].split('?', 1)[-1].split('&'):
                if 'kaisai_date' in param:
                    kaisai_date_str = param.split('=')[1]
                    break

    if not kaisai_date_str:
        return None, None, None

    tables = pd.read_html(StringIO(html_content))
    if len(tables) < 3:
        return None, None, None

    main_df = pd.DataFrame(tables[0])
    # WHY: 着順でフィルタすると「中止/失格/落馬」の馬が消え、出走頭数と行数がズレて
    #      レース内正規化・市場確率が狂う(データ監査で239レース=9%が欠落と判明)。
    #      実際に馬券市場でオッズが付いた出走馬=単勝オッズが数値の行を残す。
    #      取消/除外(非出走=オッズ無し)のみ除外される。着順は後段でNaN許容。
    if '単勝 オッズ' in main_df.columns:
        main_df = main_df[pd.to_numeric(main_df['単勝 オッズ'], errors='coerce').notna()].copy()
    else:
        main_df = main_df[pd.to_numeric(main_df['着 順'], errors='coerce').notna()].copy()
    if len(main_df) == 0:
        return None, None, None

    kaisai_date = datetime.datetime.strptime(kaisai_date_str, '%Y%m%d').replace(tzinfo=ZoneInfo('Asia/Tokyo'))

    # --- レースメタ ---
    meta = {'distance': '', 'weather': '', 'track_condition': '', 'race_place': '', 'count': '',
            'title_text': '', 'is_shinba': False, 'is_mishori': False, 'is_1win': False,
            'is_2win': False, 'is_3win': False, 'is_g3': False, 'is_g2': False, 'is_g1': False,
            'is_L': False, 'is_OP': False, 'is_win5': False}

    rd1 = soup.find('div', class_='RaceData01')
    if rd1:
        t = rd1.text.strip()
        m = re.search(r'([芝ダ障]\d+m)', t)
        if m: meta['distance'] = m.group(1)
        m = re.search(r'天候:(\S+)', t)
        if m: meta['weather'] = m.group(1)
        # WHY: 結果ページは馬場を1文字に略す(稍重→「稍」/不良→「不」)ことがあり、
        #      旧regex 馬場:(良|稍重|重|不良) は「稍」「不」を取りこぼし20%欠損した。
        #      略記・正式の両方を拾い、正規形に正規化する。
        m = re.search(r'馬場\s*[:：]\s*(不良|稍重|良|稍|重|不)', t)
        if m:
            meta['track_condition'] = {'稍': '稍重', '不': '不良'}.get(m.group(1), m.group(1))

    rd2 = soup.find('div', class_='RaceData02')
    if rd2:
        spans = [s.text.strip() for s in rd2.find_all('span')]
        for s in spans:
            cm = re.search(r'(\d+)頭', s)
            if cm: meta['count'] = cm.group(1)
            if s in ('札幌','函館','福島','新潟','東京','中山','中京','京都','阪神','小倉'):
                meta['race_place'] = s
        ta = ' '.join(spans)
        meta['is_shinba'] = '新馬' in ta
        meta['is_mishori'] = '未勝利' in ta
        meta['is_1win'] = '1勝' in ta or '500万下' in ta
        meta['is_2win'] = '2勝' in ta or '1000万下' in ta
        meta['is_3win'] = '3勝' in ta or '1600万下' in ta
        meta['is_g3'] = '(G3)' in ta or '(G３)' in ta
        meta['is_g2'] = '(G2)' in ta or '(G２)' in ta
        meta['is_g1'] = '(G1)' in ta or '(G１)' in ta
        meta['is_L'] = '(L)' in ta or 'リステッド' in ta
        meta['is_OP'] = 'オープン' in ta or 'OP' in ta

    rn = soup.find('div', class_='RaceName') or soup.find('span', class_='RaceName_main')
    if rn: meta['title_text'] = rn.text.strip()

    # --- Links ---
    horse_links = {}
    for a in soup.find_all('a', href=lambda x: x and '/horse/' in x):
        n = a.text.strip()
        if n: horse_links[n] = a['href']
    jockey_links = {}
    for a in soup.find_all('a', href=lambda x: x and '/jockey/' in x):
        n = a.text.strip()
        if n: jockey_links[n] = a['href']

    horse_df = pd.DataFrame(list(horse_links.items()), columns=['horse_name', 'horse_url'])
    jockey_df = pd.DataFrame(list(jockey_links.items()), columns=['jockey_name', 'jockey_url'])

    # --- base_df ---
    base_cols = ['枠', '馬 番', '馬名', '性齢', '斤量', '騎手', '厩舎', '馬体重 (増減)', '単勝 オッズ', '人 気']
    if any(c not in main_df.columns for c in base_cols):
        return None, None, None

    base_df = main_df[base_cols].copy()
    base_df.columns = ['frame_number', 'horse_number', 'horse_name', 'sex', 'weight',
                        'jockey_name', 'stable_name', 'body_weight', 'odds', 'popularity']
    base_df = base_df.merge(horse_df, on='horse_name', how='left')
    base_df = base_df.merge(jockey_df, on='jockey_name', how='left')

    for k, v in [('race_id', race_id), ('race_date', kaisai_date),
                  ('new_flg', meta['is_shinba']), ('not_win_flg', meta['is_mishori']),
                  ('win_1_flg', meta['is_1win']), ('win_2_flg', meta['is_2win']),
                  ('win_3_flg', meta['is_3win']), ('g3_flg', meta['is_g3']),
                  ('g2_flg', meta['is_g2']), ('g1_flg', meta['is_g1']),
                  ('l_flg', meta['is_L']), ('op_flg', meta['is_OP']),
                  ('is_win5', meta['is_win5']), ('event_title', meta['title_text']),
                  ('distance', meta['distance']), ('weather', meta['weather']),
                  ('track_condition', meta['track_condition']),
                  ('race_place', meta['race_place']), ('count', meta['count'])]:
        base_df[k] = v

    base_df['age'] = base_df['sex'].apply(lambda v: int(m.group(1)) if (m := re.search(r'(\d+)', str(v))) else None)
    base_df['sex'] = base_df['sex'].apply(lambda v: m.group(1) if (m := re.match(r'([牡牝セ]+)', str(v))) else str(v))
    base_df['body_weight_diff'] = base_df['body_weight'].apply(lambda v: int(m.group(1)) if (m := re.search(r'\(([-+]?\d+)\)', str(v))) else None)
    base_df['body_weight'] = base_df['body_weight'].apply(lambda v: m.group(1) if (m := re.match(r'(\d+)', str(v))) else v)

    d = meta['distance']
    base_df['field_type'] = 'turf' if '芝' in d else ('dirt' if 'ダ' in d else ('jump' if '障' in d else None))
    dm = re.search(r'(\d+)', d)
    base_df['distance_m'] = int(dm.group(1)) if dm else None

    # WHY: ページの「N頭」は除外/取消馬を含む登録頭数のことがあり、実走頭数とズレる。
    #      出走頭数=実際に走った頭数(=オッズ付き行数)に揃え、枠順比率等のレース内特徴を正す。
    base_df['count'] = len(base_df)

    # --- result_df (払戻金付き + 後3F + 着差) ---
    result_cols = ['馬 番', '馬名', '着 順', 'タイム', 'コーナー 通過順']
    rdf = main_df[result_cols].copy()
    rdf.columns = ['horse_number', 'horse_name', 'rank', 'race_time', 'corner_order']
    rdf['race_id'] = race_id

    # 後3F（上がり3ハロン）
    if '後3F' in main_df.columns:
        rdf['last_3f'] = main_df['後3F'].values
    else:
        rdf['last_3f'] = None

    # 着差
    if '着差' in main_df.columns:
        rdf['margin'] = main_df['着差'].values
    else:
        rdf['margin'] = None

    # 払戻金を全行にmerge
    payouts = parse_payouts(tables)
    payouts['race_date'] = kaisai_date_str
    payouts['race_id'] = race_id
    pay_df = pd.DataFrame([payouts])
    result_df = rdf.merge(pay_df, on='race_id', how='inner')

    return base_df, result_df, kaisai_date_str


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, default=None)
    parser.add_argument('--limit', type=int, default=0)
    # ブロック対策: 待機・休憩を調整可能に(既定=安全側)。大規模(1-2年)は --safe 推奨。
    parser.add_argument('--min-delay', type=float, default=3.0, help='レース間最小待機秒')
    parser.add_argument('--max-delay', type=float, default=10.0, help='レース間最大待機秒')
    parser.add_argument('--rest-every', type=int, default=50, help='N件ごとに長休憩')
    parser.add_argument('--rest-min', type=float, default=60.0, help='長休憩 最小秒')
    parser.add_argument('--rest-max', type=float, default=120.0, help='長休憩 最大秒')
    parser.add_argument('--safe', action='store_true',
                        help='超安全モード(5-15秒待機/30件ごとに120-240秒休憩)')
    args = parser.parse_args()

    if args.safe:
        args.min_delay, args.max_delay = 5.0, 15.0
        args.rest_every, args.rest_min, args.rest_max = 30, 120.0, 240.0
    logger.info(f'待機={args.min_delay}-{args.max_delay}秒 / {args.rest_every}件ごとに{args.rest_min:.0f}-{args.rest_max:.0f}秒休憩')

    qs = URLMst.objects.filter(status='pending').order_by('race_date', 'race_id')
    if args.year:
        qs = qs.filter(race_id__startswith=str(args.year))
    pending = list(qs.values_list('url', 'race_id'))
    if args.limit > 0:
        pending = pending[:args.limit]

    logger.info(f'Pending: {len(pending)} races')
    if not pending:
        return

    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'odds'), exist_ok=True)
    success = errors = skipped = 0
    consecutive_errors = 0
    import glob as glob_mod

    for i, (url, race_id) in enumerate(pending):
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            blocked = check_ip_blocked()
            logger.error(f'連続エラー{consecutive_errors}回 {"+ IPブロック" if blocked else ""} → 強制停止')
            break

        try:
            result_url = url.replace('shutuba', 'result')
            odds_file = os.path.join(settings.MEDIA_ROOT, 'odds', f'{race_id}.html')

            # キャッシュ確認
            html = ''
            fetched = False
            existing = glob_mod.glob(os.path.join(settings.MEDIA_ROOT, 'odds', f'*{race_id}*.html'))
            if existing:
                with open(existing[0], 'r', encoding='utf-8', errors='ignore') as f:
                    html = f.read()
                if '<title>race.netkeiba.com</title>' in html[:2000] or len(html) < 500:
                    html = ''
                    os.remove(existing[0])

            if not html:
                html = fetch_html(result_url)
                fetched = True
                if not html:
                    errors += 1
                    consecutive_errors += 1
                    logger.warning(f'{race_id}: fetch failed')
                    continue

            if any(kw in html for kw in ['ページが見つかりません', 'お探しのページは', 'Not Found', 'エラーが発生']):
                update_status(race_id, 'not_found')
                skipped += 1
                consecutive_errors = 0
                continue

            base_df, result_df, kaisai_date = process_result_page(html, race_id)
            if base_df is None:
                update_status(race_id, 'not_found')
                skipped += 1
                consecutive_errors = 0
                continue

            if len(base_df) != len(result_df):
                skipped += 1
                consecutive_errors = 0
                continue

            insert_base_db(base_df, USERNAME)
            insert_result_db(result_df, USERNAME)

            if fetched:
                with open(odds_file, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(html)

            update_status(race_id, 'ok')
            success += 1
            consecutive_errors = 0

        except Exception as e:
            errors += 1
            consecutive_errors += 1
            logger.warning(f'{race_id}: {type(e).__name__}: {str(e)[:120]}')

        # Bot対策: ランダム待機(CLIで調整可)
        time.sleep(random.uniform(args.min_delay, args.max_delay))

        if (i + 1) % args.rest_every == 0:
            long_wait = random.uniform(args.rest_min, args.rest_max)
            logger.info(f'[{i+1}/{len(pending)}] ok:{success} err:{errors} skip:{skipped} → {long_wait:.0f}秒休憩')
            time.sleep(long_wait)
        elif (i + 1) % 20 == 0:
            logger.info(f'[{i+1}/{len(pending)}] ok:{success} err:{errors} skip:{skipped}')

    logger.info(f'Done: ok={success} err={errors} skip={skipped}')
    logger.info(f'DB rows: {BaseData.objects.count()} / pending残: {URLMst.objects.filter(status="pending").count()}')


if __name__ == '__main__':
    main()
