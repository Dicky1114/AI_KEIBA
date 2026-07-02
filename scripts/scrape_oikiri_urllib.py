#!/usr/bin/env python3
"""
@file    scrape_oikiri_urllib.py
@brief   調教(追い切り)評価を urllib で取得 → CSV化(build_dataset_pandas が結合)
@version 1.0.0  2026-06-28  新規作成 (Dicky1114)

なぜ:
  調教評価(仕上がりS/A/B等)は陣営の状態判断で、市場(オッズ)が一様に消化しない
  =ΔLLを＋にできる候補(リサーチ「市場が軽視する情報トップ5」)。
  oikiri.html?race_id= は JS不要(UTF-8)で table[0] に 枠/馬番/印/馬名/評価/評価 を持つ。

出力:
  - 生HTML: media/oikiri/{race_id}.html (網羅保存=再パース可)
  - 評価CSV: media/csv_export/oikiri_grades.csv (race_id,horse_number,oikiri_grade,oikiri_mark)

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/scrape_oikiri_urllib.py [--limit N]
"""

import os
import sys
import re
import csv
import time
import random
import logging
import argparse
from urllib import request, error as urllib_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

import pandas as pd
from io import StringIO
from django.conf import settings
from app_folder.models import URLMst

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

GRADE_MAP = {'S': 4, 'A': 3, 'B': 2, 'C': 1, 'D': 0}
OIKIRI_DIR = os.path.join(settings.MEDIA_ROOT, 'oikiri')
OUT_CSV = os.path.join(settings.MEDIA_ROOT, 'csv_export', 'oikiri_grades.csv')


def fetch(url, retries=3):
    for a in range(retries + 1):
        try:
            req = request.Request(url, headers={'User-Agent': random.choice(settings.USER_AGENTS)})
            raw = request.urlopen(req, timeout=20).read()
            head = raw[:2000].decode('ascii', 'ignore')
            m = re.search(r'charset=["\']?([\w-]+)', head, re.I)
            return raw.decode(m.group(1) if m else 'utf-8', 'ignore')
        except urllib_error.HTTPError as e:
            if e.code in (403, 429, 503) and a < retries:
                time.sleep(30 * (2 ** a) + random.uniform(0, 10)); continue
            return None
        except Exception:
            if a < retries:
                time.sleep(30 * (2 ** a)); continue
            return None
    return None


def parse_grades(html, race_id):
    """table[0] から (horse_number, grade_num, mark) を抽出。"""
    try:
        tabs = pd.read_html(StringIO(html))
    except (ValueError, ImportError):
        return []
    if not tabs:
        return []
    t = tabs[0]
    cols = [str(c) for c in t.columns]
    # 馬番列
    hn_col = next((c for c in t.columns if '馬' in str(c) and '番' in str(c)), None)
    eval_cols = [c for c in t.columns if '評価' in str(c)]
    if hn_col is None or not eval_cols:
        return []
    # 2つの評価列を「文字グレード列」と「コメント列」に判別する:
    #   グレード列 = 値が単一の S/A/B/C/D に一致する割合が高い列
    grade_col = comment_col = None
    best = -1.0
    for ec in eval_cols:
        vals = t[ec].astype(str).str.strip().str.upper()
        ratio = vals.str.fullmatch(r'[SABCD]').mean()
        if ratio > best:
            best = ratio; grade_col = ec
    comment_col = next((c for c in eval_cols if c != grade_col), None)

    rows = []
    for _, r in t.iterrows():
        try:
            hn = int(re.search(r'\d+', str(r[hn_col])).group())
        except (ValueError, AttributeError, TypeError):
            continue
        g = str(r[grade_col]).strip().upper() if grade_col is not None else ''
        mm = re.search(r'[SABCD]', g)
        grade = GRADE_MAP.get(mm.group()) if mm else ''
        comment = re.sub(r'前走', '', str(r[comment_col])).strip() if comment_col is not None else ''
        if comment.lower() == 'nan':
            comment = ''
        sent = sentiment(comment)
        rows.append((race_id, hn, grade, comment, sent))
    return rows


POS = ['絶好調', '気配抜群', '態勢万全', '万全', '上々', '良好', '好調', '本調子',
       '抜群', '上昇', '良化', '文句なし', '充実', '上向', '好気配', '気配良',
       '仕上良', '好調子', '上々', '上昇度', '反応良', '動き良', '攻め良']
NEG = ['目立たず', '平行線', '平凡', '物足り', '案外', '一息', '太め', '余裕欲',
       '物足', '見劣', '緩め']


def sentiment(comment: str) -> int:
    """調教コメントの気配スコア(好材料 - 悪材料)。"""
    if not comment:
        return ''
    s = sum(1 for k in POS if k in comment) - sum(1 for k in NEG if k in comment)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--min-delay', type=float, default=3.0)
    ap.add_argument('--max-delay', type=float, default=10.0)
    args = ap.parse_args()

    os.makedirs(OIKIRI_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

    # 取得済み(ok)レースを対象。既にCSVにあるrace_idはスキップ。
    done = set()
    if os.path.exists(OUT_CSV):
        prev = pd.read_csv(OUT_CSV, dtype=str)
        done = set(prev['race_id'].unique())
    race_ids = list(URLMst.objects.filter(status='ok').order_by('race_date', 'race_id')
                    .values_list('race_id', flat=True))
    targets = [r for r in race_ids if r not in done]
    if args.limit:
        targets = targets[:args.limit]
    logger.info(f"調教取得対象: {len(targets)} レース (済 {len(done)})")

    new_file = not os.path.exists(OUT_CSV)
    f = open(OUT_CSV, 'a', newline='', encoding='utf-8')
    w = csv.writer(f)
    if new_file:
        w.writerow(['race_id', 'horse_number', 'oikiri_grade', 'oikiri_comment', 'oikiri_sentiment'])

    ok = empty = err = 0
    for i, rid in enumerate(targets):
        cache = os.path.join(OIKIRI_DIR, f'{rid}.html')
        html = None
        if os.path.exists(cache):
            with open(cache, encoding='utf-8', errors='ignore') as cf:
                html = cf.read()
        if not html:
            html = fetch(f"https://race.netkeiba.com/race/oikiri.html?race_id={rid}")
            if not html:
                err += 1
                time.sleep(random.uniform(args.min_delay, args.max_delay))
                continue
            with open(cache, 'w', encoding='utf-8', errors='ignore') as cf:
                cf.write(html)
            time.sleep(random.uniform(args.min_delay, args.max_delay))
        rows = parse_grades(html, rid)
        graded = [r for r in rows if r[2] != '']
        if rows:
            w.writerows(rows); f.flush()
            ok += 1 if graded else 0
            empty += 0 if graded else 1
        else:
            empty += 1
        if (i + 1) % 50 == 0:
            logger.info(f"[{i+1}/{len(targets)}] grade有:{ok} grade無:{empty} err:{err}")
            time.sleep(random.uniform(60, 120))
    f.close()
    logger.info(f"完了: grade有レース={ok} grade無={empty} err={err} → {OUT_CSV}")


if __name__ == '__main__':
    main()
