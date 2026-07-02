#!/usr/bin/env python3
"""
@file    reparse_cached.py
@brief   キャッシュ済みHTML(media/odds)を修正版パーサで再パース→DB上書き(冪等)
@version 1.0.0  2026-06-30  (Dicky1114)

なぜ: データ監査で「中止/失格馬の脱落(9%レースで頭数欠落)」「馬場略記の取りこぼし(20%)」
      が判明。scrape_urllib.py を修正済み。既存データはキャッシュHTMLから再パースすれば
      ネット再取得なしで一気にクリーン化できる(insert_*_dbはupsert=重複しない)。
      sleep無し・キャッシュのみなのでブロックリスク無し・高速。

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/reparse_cached.py
"""
import os, sys, glob, logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
import django  # noqa
django.setup()
from django.conf import settings
from scripts.scrape_urllib import process_result_page
from app_folder.services.insert_db import insert_base_db, insert_result_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
USER = 'reparse_fix'


def main():
    files = sorted(glob.glob(os.path.join(settings.MEDIA_ROOT, 'odds', '*.html')))
    logger.info(f'キャッシュHTML {len(files)}件を再パース')
    ok = fixed_horse = skip = err = 0
    for i, f in enumerate(files):
        rid = os.path.basename(f).replace('.html', '')
        if not rid.isdigit():
            continue
        try:
            html = open(f, encoding='utf-8', errors='ignore').read()
            base, result, kd = process_result_page(html, rid)
            if base is None or len(base) != len(result):
                skip += 1
                continue
            insert_base_db(base, USER)
            insert_result_db(result, USER)
            ok += 1
        except Exception as e:
            err += 1
            if err <= 5:
                logger.warning(f'{rid}: {type(e).__name__}: {str(e)[:100]}')
        if (i + 1) % 200 == 0:
            logger.info(f'  {i+1}/{len(files)} ok={ok} skip={skip} err={err}')
    logger.info(f'完了: ok={ok} skip={skip} err={err}')


if __name__ == '__main__':
    main()
