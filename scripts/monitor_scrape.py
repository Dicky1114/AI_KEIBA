#!/usr/bin/env python3
"""
@file    monitor_scrape.py
@brief   5年スクレイプ中の「新規取得データ」の品質を監査し、健全性を1行で報告
@version 1.0.0  2026-06-30  (Dicky1114)

なぜ: 30時間スクレイプを盲目的に回さず、取得データが正しいか定期チェックし、
      おかしければ即停止できるようにする(古い年の形式違い・ブロックによるゴミ混入を早期検知)。

チェック対象 = 新規取得分(race_date < 2025-10-04 = 今回の2021-2025スクレイプ分)。
判定:
  OK   : 頭数一致>=98% / 馬場欠損<5% / オッズ欠損<2% / ゴミ無し
  WARN : しきい値を少し外れる
  STOP : 頭数一致<85% or オッズ欠損>15% or ゴミ多発 → 取得が壊れている疑い

終了コード: 0=OK/WARN, 2=STOP(壊れている)。watcherがこれを見て自動停止できる。

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/monitor_scrape.py
"""
import os, sys, logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
import django  # noqa
django.setup()
from django.db import connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
NEW_CUTOFF = '2025-10-04'  # これより前 = 今回の新規スクレイプ分


def q(sql):
    with connection.cursor() as c:
        c.execute(sql)
        return c.fetchall()


def main():
    # 進捗
    prog = dict(q("SELECT status, count(*) FROM m_url GROUP BY status"))
    ok = prog.get('ok', 0); pending = prog.get('pending', 0)
    nf = prog.get('not_found', 0)
    total = ok + pending + nf

    # 新規分の品質
    base_new = f"FROM t_base_info WHERE race_date < '{NEW_CUTOFF}'"
    n_rows = q(f"SELECT count(*) {base_new}")[0][0]
    n_races = q(f"SELECT count(distinct race_id) {base_new}")[0][0]
    if n_races == 0:
        print("新規取得データまだ無し(2021-2025の取得開始待ち)")
        return 0

    # 頭数一致率
    mism = q(f"""
      WITH a AS (SELECT race_id, max(count::int) d, count(*) ac
                 FROM t_base_info WHERE race_date < '{NEW_CUTOFF}' GROUP BY race_id)
      SELECT count(*) FILTER (WHERE d<>ac), count(*) FROM a""")[0]
    mismatch, racetot = mism
    head_ok = 100 * (racetot - mismatch) / racetot if racetot else 0

    # 馬場欠損率(レース単位)
    baba_null = q(f"SELECT count(distinct race_id) {base_new} AND (track_condition IS NULL OR track_condition='')")[0][0]
    baba_miss = 100 * baba_null / n_races

    # オッズ欠損率(行単位)
    odds_null = q(f"SELECT count(*) {base_new} AND (odds IS NULL OR odds='')")[0][0]
    odds_miss = 100 * odds_null / n_rows if n_rows else 0

    # ゴミ検知: 馬名空 / 結果欠損(1着不在レース)
    name_empty = q(f"SELECT count(*) {base_new} AND (horse_name IS NULL OR horse_name='')")[0][0]
    no_winner = q(f"""
      SELECT count(*) FROM (
        SELECT b.race_id FROM t_base_info b
        LEFT JOIN t_result_info r ON b.race_id=r.race_id AND r.rank='1'
        WHERE b.race_date < '{NEW_CUTOFF}'
        GROUP BY b.race_id HAVING count(r.rank)=0) z""")[0][0]

    # 判定
    if head_ok < 85 or odds_miss > 15 or name_empty > n_rows * 0.02:
        verdict, code = 'STOP', 2
    elif head_ok < 98 or baba_miss > 5 or odds_miss > 2 or no_winner > n_races * 0.02:
        verdict, code = 'WARN', 0
    else:
        verdict, code = 'OK', 0

    pct = 100 * ok / total if total else 0
    print(f"[{verdict}] 進捗 {ok}/{total} ({pct:.1f}%) pending={pending} | "
          f"新規 {n_races}R {n_rows}行 | 頭数一致 {head_ok:.1f}% | "
          f"馬場欠損 {baba_miss:.1f}% | オッズ欠損 {odds_miss:.2f}% | "
          f"馬名空 {name_empty} | 1着不在 {no_winner}")
    if verdict == 'STOP':
        print("  → STOP: データが壊れている疑い。スクレイプ停止を推奨。")
    return code


if __name__ == '__main__':
    sys.exit(main())
