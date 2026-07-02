#!/usr/bin/env python3
"""
@file    scrape_pedigree_urllib.py
@brief   血統(父・母父)を urllib で取得 → CSV化。build_dataset が結合。
@version 1.0.0  2026-06-29 (Dicky1114)

db.netkeiba.com/horse/ped/{id}/ の血統表(table.blood_table)を read_html でグリッド化:
  父   = iloc[0,0]
  母   = iloc[nrows//2, 0]
  母父 = iloc[nrows//2, 1]
出力: media/csv_export/pedigree.csv (horse_id, sire, broodmare_sire)
resume: 既にCSVにある horse_id はskip。
使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/scrape_pedigree_urllib.py [--limit N]
"""
import os, sys, re, csv, time, random, logging, argparse
from urllib import request, error as urllib_error
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
import django; django.setup()
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from django.conf import settings
from app_folder.models import BaseData
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
OUT = os.path.join(settings.MEDIA_ROOT, 'csv_export', 'pedigree.csv')
PED_DIR = os.path.join(settings.MEDIA_ROOT, 'ped')


def fetch(url, retries=3):
    for a in range(retries + 1):
        try:
            req = request.Request(url, headers={'User-Agent': random.choice(settings.USER_AGENTS)})
            raw = request.urlopen(req, timeout=20).read()
            head = raw[:1500].decode('ascii', 'ignore')
            m = re.search(r'charset=["\']?([\w-]+)', head, re.I)
            return raw.decode(m.group(1) if m else 'EUC-JP', 'ignore')
        except urllib_error.HTTPError as e:
            if e.code in (403, 429, 503) and a < retries:
                time.sleep(30*(2**a)+random.uniform(0, 10)); continue
            return None
        except Exception:
            if a < retries:
                time.sleep(20*(2**a)); continue
            return None
    return None


def clean(name):
    """種牡馬名キーを正規化。外国産(ラテン名)も残す。年/毛色/nav/国タグのみ除去。"""
    if not isinstance(name, str):
        return ''
    n = name.strip()
    n = re.sub(r'\[血統\]|\[産駒\]|系$', '', n)       # nav除去
    n = re.sub(r'\d.*$', '', n)                       # 年(数字)以降=毛色等を除去
    n = re.sub(r'\([米愛英仏豪伊独新加]\)\s*$', '', n)  # 末尾の国タグ除去
    return n.strip()


def parse_ped(html):
    """父=blood_table最初の馬リンク(確実)。母父=read_htmlグリッド iloc[nr//2, 1]。"""
    soup = BeautifulSoup(html, 'html.parser')
    tbl = soup.find('table', class_=re.compile('blood_table'))
    if tbl is None:
        return None, None
    links = [a.get_text(strip=True) for a in tbl.find_all('a', href=re.compile(r'/horse/(?:ped/)?\w'))
             if a.get_text(strip=True) and a.get_text(strip=True) not in ('血統', '産駒')]
    sire = clean(links[0]) if links else None
    bms = None
    try:
        df = pd.read_html(StringIO(str(tbl)))[0]
        nr = df.shape[0]
        if df.shape[1] > 1 and nr >= 2:
            bms = clean(str(df.iloc[nr // 2, 1])) or None
    except (ValueError, ImportError, IndexError, KeyError):
        bms = None
    return sire or None, bms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--min-delay', type=float, default=2.0)
    ap.add_argument('--max-delay', type=float, default=6.0)
    args = ap.parse_args()
    os.makedirs(PED_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    # 対象 horse_id (出走馬の horse_url から)
    hids = set()
    for u in BaseData.objects.exclude(horse_url__isnull=True).exclude(horse_url='').values_list('horse_url', flat=True):
        m = re.search(r'/horse/(\w+)', u)
        if m:
            hids.add(m.group(1))
    done = set()
    if os.path.exists(OUT):
        done = set(pd.read_csv(OUT, dtype=str)['horse_id'].unique())
    targets = sorted(hids - done)
    if args.limit:
        targets = targets[:args.limit]
    logger.info(f"血統取得対象: {len(targets)}頭 (済 {len(done)} / 全 {len(hids)})")

    new = not os.path.exists(OUT)
    f = open(OUT, 'a', newline='', encoding='utf-8'); w = csv.writer(f)
    if new:
        w.writerow(['horse_id', 'sire', 'broodmare_sire'])
    ok = err = 0
    for i, hid in enumerate(targets):
        cache = os.path.join(PED_DIR, f'{hid}.html')
        html = None
        if os.path.exists(cache):
            html = open(cache, encoding='utf-8', errors='ignore').read()
        if not html:
            html = fetch(f"https://db.netkeiba.com/horse/ped/{hid}/")
            if not html:
                err += 1; time.sleep(random.uniform(args.min_delay, args.max_delay)); continue
            open(cache, 'w', encoding='utf-8', errors='ignore').write(html)
            time.sleep(random.uniform(args.min_delay, args.max_delay))
        sire, bms = parse_ped(html)
        w.writerow([hid, sire or '', bms or '']); f.flush()
        if sire:
            ok += 1
        if (i+1) % 100 == 0:
            logger.info(f"[{i+1}/{len(targets)}] sire有:{ok} err:{err}")
            time.sleep(random.uniform(30, 60))
    f.close()
    logger.info(f"完了: sire有={ok} err={err} → {OUT}")


if __name__ == '__main__':
    main()
