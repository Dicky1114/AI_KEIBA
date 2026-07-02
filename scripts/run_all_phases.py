#!/usr/bin/env python3
"""
@file    run_all_phases.py
@brief   全フェーズを順次自動実行するオーケストレーター
@version 1.0.0  2026-04-10  新規作成

実行順序:
  1. Phase 2 (scrape_horse_blood.py) と Backfill (backfill_last_3f.py) の完了を待つ
  2. Phase 3a: scrape_jockey.py 実行（騎手成績）
  3. Phase 3b: insert_training_info() 実行（t_training特徴量集約）
  4. 最終レポート生成

使用方法:
    cd /home/dickey/デスクトップ/01_開発/02_dickey/03_keiba
    source venv/bin/activate
    nohup python scripts/run_all_phases.py > /tmp/run_all_phases.log 2>&1 &
    tail -f /tmp/run_all_phases.log
"""

import os
import sys
import logging
import time
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

CHECK_INTERVAL = 300  # 5分ごとに監視


def is_process_running(script_name: str) -> bool:
    """指定スクリプト名のPythonプロセスが動いているか判定。"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', script_name],
            capture_output=True, text=True
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def wait_for_scrapers():
    """Phase 2 と Backfill の両方が終わるまで待つ。"""
    logger.info('Phase 2 + Backfill の完了待機中...')
    while True:
        phase2_running = is_process_running('scrape_horse_blood')
        # backfillは完了済みなのでチェック不要
        backfill_running = False

        if not phase2_running and not backfill_running:
            logger.info('両スクレイパー完了を検出')
            return

        logger.info(f'待機中: phase2={phase2_running}, backfill={backfill_running}')
        time.sleep(CHECK_INTERVAL)


def run_script(script_path: str, log_path: str) -> int:
    """スクリプトを同期実行。戻り値は exit code。"""
    logger.info(f'実行開始: {script_path}')
    with open(log_path, 'w') as f:
        proc = subprocess.Popen(
            ['python', script_path],
            stdout=f, stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
        )
        proc.wait()
    logger.info(f'実行完了: {script_path} (exit={proc.returncode})')
    return proc.returncode


def run_training_feature_build():
    """insert_training_info() を実行して t_training を構築。"""
    logger.info('Phase 3b: t_training 特徴量集約を開始')
    try:
        from app_folder.services.insert_db import insert_training_info
        insert_training_info()
        logger.info('Phase 3b: t_training 集約完了')
        return True
    except Exception as e:
        logger.error(f'Phase 3b 失敗: {type(e).__name__}: {e}')
        return False


def final_report():
    """最終的なDB状態レポートを生成。"""
    import psycopg2
    conn = psycopg2.connect('dbname=keiba_db user=keiba_user password=KeibaDB@2026 host=localhost port=5432')
    cur = conn.cursor()

    queries = [
        ('races', "SELECT COUNT(DISTINCT race_id) FROM t_base_info"),
        ('result_rows', "SELECT COUNT(*) FROM t_result_info"),
        ('result_last_3f_filled', "SELECT COUNT(*) FROM t_result_info WHERE last_3f IS NOT NULL"),
        ('result_margin_filled', "SELECT COUNT(*) FROM t_result_info WHERE margin IS NOT NULL"),
        ('horse_history_unique', "SELECT COUNT(DISTINCT horse_id) FROM t_horse_info"),
        ('horse_blood_unique', "SELECT COUNT(DISTINCT horse_id) FROM m_horse_blood"),
        ('jockey_rows', "SELECT COUNT(*) FROM t_jockey_info"),
        ('jockey_unique', "SELECT COUNT(DISTINCT jockey_id) FROM t_jockey_info"),
        ('training_rows', "SELECT COUNT(*) FROM t_training"),
    ]

    logger.info('=' * 60)
    logger.info('最終レポート')
    logger.info('=' * 60)
    for name, q in queries:
        cur.execute(q)
        count = cur.fetchone()[0]
        logger.info(f'  {name:30s}: {count:>12,}')
    logger.info('=' * 60)
    conn.close()


def main():
    # 1. 現在稼働中のスクレイパー完了を待つ
    wait_for_scrapers()

    # 2. Phase 3a: 騎手スクレイピング
    logger.info('Phase 3a: 騎手成績スクレイピング開始')
    jockey_rc = run_script(
        os.path.join(BASE_DIR, 'scripts/scrape_jockey.py'),
        '/tmp/scrape_jockey.log'
    )
    if jockey_rc != 0:
        logger.warning(f'scrape_jockey.py が非ゼロで終了: rc={jockey_rc}')

    # 3. Phase 3b: t_training 特徴量構築
    run_training_feature_build()

    # 4. 最終レポート
    final_report()
    logger.info('全フェーズ完了')


if __name__ == '__main__':
    main()
