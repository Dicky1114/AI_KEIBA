#!/usr/bin/env python3
"""
@file    extract_race_class.py
@brief   キャッシュ済みレースHTML(media/odds)から「クラス(条件)」を抽出してCSV化
@version 1.0.0  2026-06-30  (Dicky1114)

背景: t_base_info の win_1/2/3_flg・g1/g2/g3_flg・l_flg は全行Falseで死んでいる
      (スクレイパ未セット)。クラスは強力な予測子なのでHTMLタイトルから復元する。
      クラスは出走前に既知=リーク無しでそのまま特徴量にできる。

出力: media/csv_export/race_class.csv  (race_id, race_class, class_level)
  class_level: 新馬0/未勝利1/1勝2/2勝3/3勝4/OP/L5/G3=6/G2=7/G1=8 (能力序列の順序数)
"""
import os, sys, re, glob, logging, unicodedata
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
import django  # noqa
django.setup()
from django.conf import settings
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 判定は強い順(上から先にマッチ)。class_level=能力序列。
RULES = [
    ('G1', 'G1', 8), ('G2', 'G2', 7), ('G3', 'G3', 6),
    ('リステッド', 'L', 5), ('(L)', 'L', 5),
    ('オープン', 'OP', 5), ('OP', 'OP', 5),
    ('3勝クラス', '3勝', 4), ('1600万', '3勝', 4),
    ('2勝クラス', '2勝', 3), ('1000万', '2勝', 3),
    ('1勝クラス', '1勝', 2), ('500万', '1勝', 2),
    ('未勝利', '未勝利', 1),
    ('新馬', '新馬', 0),
]


def classify(title: str):
    # 全角数字・記号を半角化(「１勝クラス」→「1勝クラス」)してからキーワード照合
    t = unicodedata.normalize('NFKC', title or '')
    for kw, name, lvl in RULES:
        if kw in t:
            return name, lvl
    return '不明', -1


def main():
    odds_dir = os.path.join(settings.MEDIA_ROOT, 'odds')
    files = glob.glob(os.path.join(odds_dir, '*.html'))
    logger.info(f"HTML {len(files)}件を解析")
    rows = []
    miss = 0
    for f in files:
        rid = os.path.basename(f).replace('.html', '')
        try:
            h = open(f, encoding='utf-8', errors='ignore').read(4000)  # 先頭で十分(title)
        except OSError:
            continue
        m = re.search(r'<title>(.*?)</title>', h)
        title = m.group(1) if m else ''
        name, lvl = classify(title)
        if lvl < 0:
            miss += 1
        rows.append({'race_id': rid, 'race_class': name, 'class_level': lvl})
    out = pd.DataFrame(rows)
    path = os.path.join(settings.MEDIA_ROOT, 'csv_export', 'race_class.csv')
    out.to_csv(path, index=False)
    logger.info(f"出力: {path}  ({len(out)}件 / 不明{miss}件)")
    logger.info("クラス分布:\n" + out['race_class'].value_counts().to_string())


if __name__ == '__main__':
    main()
