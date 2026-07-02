#!/bin/bash
# @file stop_scrape.sh
# @brief 5年スクレイプと監視ウォッチャーを即停止する(コンテナにkill/pkill無いためos.kill使用)
# 使用: ! bash scripts/stop_scrape.sh
cd "/home/dickey/デスクトップ/01_開発/02_dickey/03_keiba" || exit 1
# コンテナ内 scrape プロセスを停止
pids=$(docker compose exec -T web sh -c 'for p in /proc/[0-9]*; do c=$(tr "\0" " " < $p/cmdline 2>/dev/null); echo "$c" | grep -q scrape_urllib && echo ${p##*/}; done' 2>/dev/null | tr "\n" " ")
if [ -n "$pids" ]; then
  docker compose exec -T web python3 -c "import os,signal
for x in '$pids'.split():
    try: os.kill(int(x), signal.SIGTERM); print('stopped scrape pid', x)
    except Exception as e: print(e)" 2>/dev/null
else
  echo "scrapeプロセスは見つかりませんでした(既に停止?)"
fi
# 監視ウォッチャーを停止
pkill -f monitor_watch.sh 2>/dev/null && echo "監視ウォッチャー停止"
echo "停止完了。再開するには: nohup docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop web python scripts/scrape_urllib.py --min-delay 3 --max-delay 7 --rest-every 50 --rest-min 40 --rest-max 80 > logs/scrape_5y.log 2>&1 &"
