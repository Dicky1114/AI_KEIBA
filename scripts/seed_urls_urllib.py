#!/usr/bin/env python3
"""
@file    seed_urls_urllib.py
@brief   Selenium不使用でURLMst(m_url)に対象レースURLをseedするスクリプト
@version 1.0.0  2026-06-28  新規作成 (Dicky1114)

経緯:
  既存 GetRaceID.get_race_ids() は race_list.html を driver.get で取得するが、
  同ページはJS描画のため urllib では race_id を取得できない。
  netkeiba の Ajax エンドポイント race_list_sub.html?kaisai_date=YYYYMMDD は
  JS不要のHTML断片を返すため urllib で race_id を取得できる(実証済)。

フロー:
  1. calendar.html?year=&month= で開催日(kaisai_date)を取得 (urllib)
  2. race_list_sub.html?kaisai_date= で各開催日の race_id を取得 (urllib)
  3. URLMst へ update_or_create で投入 (status=pending・既存statusは保護)

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/seed_urls_urllib.py --start 2026-04-01 --end 2026-06-28
"""

import os
import sys
import re
import time
import random
import argparse
import logging
from datetime import datetime, date, timedelta
from urllib import request, error as urllib_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

from django.conf import settings
from django.utils import timezone
from app_folder.models import URLMst

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SYSTEM_USER = "url_seeder"
RACE_ID_RE = re.compile(r"race_id=(\d{12})")
KAISAI_RE = re.compile(r"kaisai_date=(\d{8})")


def fetch(url: str, enc: str = 'EUC-JP') -> str | None:
    """urllib でHTMLを取得する。Bot対策に軽いランダム待機を挟む。"""
    headers = dict(settings.HEADERS)
    try:
        req = request.Request(url, headers=headers)
        with request.urlopen(req, timeout=20) as resp:
            return resp.read().decode(enc, errors='ignore')
    except (urllib_error.URLError, urllib_error.HTTPError) as e:
        logger.warning(f"fetch失敗 {url}: {e}")
        return None


def month_iter(start: date, end: date):
    """start..end を跨ぐ (year, month) を列挙する。"""
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def collect_kaisai_dates(start: date, end: date) -> list[str]:
    """カレンダーから期間内の開催日(YYYYMMDD)を集める。"""
    dates: set[str] = set()
    for y, m in month_iter(start, end):
        html = fetch(f"https://race.netkeiba.com/top/calendar.html?year={y}&month={m}")
        if not html:
            continue
        for ds in KAISAI_RE.findall(html):
            d = datetime.strptime(ds, "%Y%m%d").date()
            if start <= d <= end:
                dates.add(ds)
        time.sleep(random.uniform(1, 2))
    return sorted(dates)


def collect_race_ids(kaisai_date: str) -> list[str]:
    """race_list_sub から開催日の race_id を集める。"""
    html = fetch(f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}")
    if not html:
        return []
    return sorted(set(RACE_ID_RE.findall(html)))


def main():
    parser = argparse.ArgumentParser(description="URLMst seeder (urllib, Selenium不使用)")
    parser.add_argument('--start', type=str, required=True, help='開始日 YYYY-MM-DD')
    parser.add_argument('--end', type=str, required=True, help='終了日 YYYY-MM-DD')
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()
    logger.info(f"==== URL seed 開始 {start} ~ {end} ====")

    kaisai_dates = collect_kaisai_dates(start, end)
    logger.info(f"開催日: {len(kaisai_dates)}日")

    total = 0
    new = 0
    for i, ds in enumerate(kaisai_dates):
        race_ids = collect_race_ids(ds)
        race_date = datetime.strptime(ds, "%Y%m%d")
        for rid in race_ids:
            url = f"{settings.URL_HEAD}{rid}"
            now = timezone.now()
            # WHY: created_at は NOT NULL かつ status は再seedで保護したいので
            #      新規は get_or_create で全項目補完、既存は race_date/url のみ更新する。
            _, created = URLMst.objects.get_or_create(
                race_id=rid,
                defaults={
                    'race_date': race_date,
                    'url': url,
                    'created_at': now,
                    'updated_at': now,
                    'created_user': SYSTEM_USER,
                    'updated_user': SYSTEM_USER,
                    'status': 'pending',
                },
            )
            if created:
                new += 1
            else:
                URLMst.objects.filter(race_id=rid).update(
                    race_date=race_date, url=url, updated_at=now, updated_user=SYSTEM_USER
                )
            total += 1
        logger.info(f"[{i+1}/{len(kaisai_dates)}] {ds}: {len(race_ids)} races (累計 {total}, 新規 {new})")
        time.sleep(random.uniform(1, 3))

    pending = URLMst.objects.filter(status='pending').count()
    logger.info(f"==== seed完了: 対象 {total} / 新規 {new} / URLMst pending {pending} ====")


if __name__ == '__main__':
    main()
