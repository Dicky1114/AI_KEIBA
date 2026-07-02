#!/bin/bash
# @file monitor_watch.sh
# @brief 5年スクレイプを30分ごとに監査。STOP判定なら自動停止。pending=0で正常終了。
# 使用: nohup bash scripts/monitor_watch.sh > /dev/null 2>&1 &
cd "/home/dickey/デスクトップ/01_開発/02_dickey/03_keiba" || exit 1
LOG="logs/monitor.log"
DC="docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop web"
echo "[$(date '+%F %H:%M')] ===== 監視開始 =====" >> "$LOG"
while true; do
  out=$($DC python scripts/monitor_scrape.py 2>/dev/null | grep -vE 'version|obsolete' | grep -E '^\[')
  echo "[$(date '+%F %H:%M')] $out" >> "$LOG"

  # STOP判定 → スクレイプ自動停止
  if echo "$out" | grep -q '\[STOP\]'; then
    pids=$(docker compose exec -T web sh -c 'for p in /proc/[0-9]*; do c=$(tr "\0" " " < $p/cmdline 2>/dev/null); echo "$c" | grep -q scrape_urllib && echo ${p##*/}; done' 2>/dev/null | tr "\n" " ")
    docker compose exec -T web python3 -c "import os,signal
for x in '$pids'.split():
    try: os.kill(int(x), signal.SIGTERM)
    except: pass" 2>/dev/null
    echo "[$(date '+%F %H:%M')] !!! AUTO-STOP: STOP判定でスクレイプ停止 (pids=$pids) !!!" >> "$LOG"
    break
  fi

  # 完了判定(pending=0)
  pend=$(docker compose exec -T db psql -U postgres -d keiba_db -t -c "SELECT count(*) FROM m_url WHERE status='pending';" 2>/dev/null | grep -oE '[0-9]+' | head -1)
  if [ "$pend" = "0" ]; then
    echo "[$(date '+%F %H:%M')] ===== スクレイプ完了 (pending=0) 監視終了 =====" >> "$LOG"
    break
  fi
  sleep 1800
done
