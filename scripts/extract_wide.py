#!/usr/bin/env python3
"""
@file    extract_wide.py
@brief   既取得の result HTML から ワイド払戻 を再抽出(再スクレイプ不要)
@version 1.0.0  2026-06-28  (Dicky1114)

ワイド払戻欄は3つ: (1着-2着), (1着-3着), (2着-3着) の順で並ぶ。
DBの着順(rank 1/2/3)から a1,a2,a3 を取り、HTMLの3払戻と対応付ける。
出力: media/csv_export/wide_payouts.csv (race_id, h_a, h_b, payout)  ※h_a<h_b
使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/extract_wide.py
"""
import os, sys, re, csv, glob, logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
import django; django.setup()
import pandas as pd
from io import StringIO
from django.conf import settings
from app_folder.models import ResultData
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
OUT = os.path.join(settings.MEDIA_ROOT, 'csv_export', 'wide_payouts.csv')


def parse_wide(html):
    """ワイドの払戻3つを順に返す([1-2,1-3,2-3])。失敗時 []。"""
    try:
        tabs = pd.read_html(StringIO(html))
    except (ValueError, ImportError):
        return []
    for t in tabs:
        for _, row in t.iterrows():
            if str(row.iloc[0]).strip() == 'ワイド':
                pay_cell = str(row.iloc[2])
                pays = [int(x.replace(',', '')) for x in re.findall(r'([\d,]+)円', pay_cell)]
                return pays
    return []


def main():
    # race_id -> (a1,a2,a3)
    res = {}
    for r in ResultData.objects.filter(rank__in=['1', '2', '3']).values('race_id', 'horse_number', 'rank'):
        res.setdefault(r['race_id'], {})[r['rank']] = str(r['horse_number'])

    files = glob.glob(os.path.join(settings.MEDIA_ROOT, 'odds', '*.html'))
    logger.info(f"HTML {len(files)}件 を再パース")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    ok = skip = 0
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['race_id', 'h_a', 'h_b', 'payout'])
        for i, path in enumerate(files):
            rid = re.search(r'(\d{12})', os.path.basename(path))
            if not rid:
                continue
            rid = rid.group(1)
            top3 = res.get(rid)
            if not top3 or not all(k in top3 for k in ('1', '2', '3')):
                skip += 1; continue
            with open(path, encoding='utf-8', errors='ignore') as cf:
                html = cf.read()
            pays = parse_wide(html)
            if len(pays) < 3:
                skip += 1; continue
            a1, a2, a3 = top3['1'], top3['2'], top3['3']
            for (x, y), p in zip([(a1, a2), (a1, a3), (a2, a3)], pays[:3]):
                ha, hb = sorted([int(x), int(y)])
                w.writerow([rid, ha, hb, p])
            ok += 1
            if (i + 1) % 500 == 0:
                logger.info(f"[{i+1}/{len(files)}] ok={ok} skip={skip}")
    logger.info(f"完了: ok={ok}レース skip={skip} → {OUT}")


if __name__ == '__main__':
    main()
