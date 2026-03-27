from datetime import date
import json
import os
import random
from pathlib import Path
import threading
import traceback
import uuid

import pandas as pd
import redis
from celery import shared_task
from celery_progress.backend import ProgressRecorder
from django.conf import settings
from django.db import transaction
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from ..models import CompareView, CreateRaceIDsView, URLMst
from ..services.get_base import get_data
from ..services.get_horse import horse_data
from ..services.get_jockey import jockey_data
from ..services.get_raceid import GetRaceID
from ..services.get_result import result
from ..services.insert_db import insert_base_db, insert_result_db, insert_url_db
from ..utils.zip import name_change, unzip_files, zip_files


class LocalAsyncResult:
    def __init__(self, task_id):
        self.id = task_id


class _LocalTaskRequest:
    def __init__(self, task_id):
        self.id = task_id


class LocalTaskContext:
    def __init__(self, task_id):
        self.request = _LocalTaskRequest(task_id)

    def update_state(self, state=None, meta=None):
        write_local_task_state(self.request.id, state=state or "PROGRESS", details=meta or {})


def set_user_agent(driver, user_agent):
    """ブラウザのUser-Agentを変更する"""
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": user_agent
})

def change_user_agent(driver, user_agents):
    random_user_agent = random.choice(user_agents)
    set_user_agent(driver, random_user_agent)
    return driver


def get_redis_client():
    redis_url = getattr(settings, "REDIS_URL", None) or getattr(settings, "CELERY_BROKER_URL", None)
    if not redis_url:
        return None
    return redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)


def get_local_task_dir():
    task_dir = Path(settings.MEDIA_ROOT) / "_task_state"
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def get_local_task_state_path(task_id):
    return get_local_task_dir() / f"{task_id}.json"


def get_local_task_stop_path(task_id):
    return get_local_task_dir() / f"{task_id}.stop"


def write_local_task_state(task_id, state, result=None, details=None):
    details = details or {}
    payload = {
        "task_id": task_id,
        "state": state,
        "status": state,
        "result": result,
        "details": details,
        "current": details.get("current", 0),
        "total": details.get("total", 0),
        "progress": details.get("current", 0),
    }
    get_local_task_state_path(task_id).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload


def read_local_task_state(task_id):
    state_path = get_local_task_state_path(task_id)
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def local_task_exists(task_id):
    return get_local_task_state_path(task_id).exists()


def set_local_task_stop(task_id):
    get_local_task_stop_path(task_id).write_text("1", encoding="utf-8")


def is_local_task_stopped(task_id):
    return get_local_task_stop_path(task_id).exists()


def clear_local_task_stop(task_id):
    stop_path = get_local_task_stop_path(task_id)
    if stop_path.exists():
        stop_path.unlink()


def start_local_task(task_name, target, *args):
    task_id = f"local-{task_name}-{uuid.uuid4()}"
    write_local_task_state(task_id, "PENDING")

    def runner():
        try:
            write_local_task_state(task_id, "STARTED")
            result = target(task_id, *args)
            write_local_task_state(task_id, "SUCCESS", result=result or "完了")
        except Exception as exc:
            write_local_task_state(
                task_id,
                "FAILURE",
                result=str(exc),
                details={"traceback": traceback.format_exc()},
            )
        finally:
            clear_local_task_stop(task_id)

    threading.Thread(target=runner, daemon=True, name=f"ai-keiba-{task_name}-{task_id}").start()
    return LocalAsyncResult(task_id)


def ensure_media_dirs():
    for subdir in ["", "base", "odds", "horse", "jockey", "calendar_yyyymm", "calendar_yyyymmdd"]:
        os.makedirs(os.path.join(settings.MEDIA_ROOT, subdir), exist_ok=True)


def create_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)


def maybe_unzip(folder_name, year=None, target=""):
    folder_path = os.path.join(settings.MEDIA_ROOT, folder_name)
    if not os.path.isdir(folder_path):
        return
    zip_count = len([f for f in os.listdir(folder_path) if f.endswith(".zip") and (year is None or str(year) in f)])
    if zip_count > 0:
        unzip_files(year, settings.MEDIA_ROOT, folder_name, target)


def maybe_zip(folder_name):
    folder_path = os.path.join(settings.MEDIA_ROOT, folder_name)
    if not os.path.isdir(folder_path):
        return
    html_count = len([f for f in os.listdir(folder_path) if f.endswith(".html")])
    if html_count > 0:
        zip_files(settings.MEDIA_ROOT, folder_name)


def build_pending_race_pairs(start_date: date, end_date: date, username: str):
    ensure_media_dirs()
    maybe_unzip("calendar_yyyymm", target="")
    maybe_unzip("calendar_yyyymmdd", target="")

    driver = create_chrome_driver()
    try:
        race_service = GetRaceID()
        url_list, race_id_list, dates_list = race_service.create_url_list(start_date, end_date, driver)
    finally:
        driver.quit()

    if url_list == "sys_err":
        raise RuntimeError("URL取得に失敗しました。")

    url_df = pd.DataFrame(
        {"race_id": race_id_list, "race_date": dates_list, "url": url_list}
    ).drop_duplicates(subset=["race_id", "race_date", "url"]).sort_values("race_date").reset_index(drop=True)

    if insert_url_db(url_df, username=username) == "sys_err":
        raise RuntimeError("URL登録に失敗しました。")

    url_race_id_pairs = URLMst.objects.exclude(
        race_id__in=CompareView.objects.values("race_id")
    ).order_by("race_id").values_list("url", "race_id")

    race_id_url_pairs = CreateRaceIDsView.objects.exclude(
        race_id__in=["202404030612", "202408060108"]
    ).values_list("url", "race_id")

    maybe_zip("calendar_yyyymm")
    maybe_zip("calendar_yyyymmdd")

    return sorted(list(url_race_id_pairs) + list(race_id_url_pairs), key=lambda x: x[1])


def run_base_scrape(task, username, url_race_id_pairs):
    redis_client = get_redis_client()
    progress_recorder = ProgressRecorder(task)
    zip_folder = settings.MEDIA_ROOT
    year = None
    task_id = getattr(getattr(task, "request", None), "id", None)
    driver = create_chrome_driver()

    try:
        total = len(url_race_id_pairs)
        for i, (url, race_id) in enumerate(url_race_id_pairs):
            if (
                task_id
                and redis_client
                and redis_client.get(f"stop:{task_id}")
            ) or (task_id and is_local_task_stopped(task_id)):
                maybe_zip("base")
                maybe_zip("odds")
                return "停止しました。"

            progress_recorder.set_progress(i + 1, total, f"{i + 1}/{total} 件 処理中...")
            driver = change_user_agent(driver, settings.USER_AGENTS)

            current_year = race_id[:4]
            if year is None:
                year = current_year
                maybe_unzip("base", year=year)
                maybe_unzip("odds", year=year)
            elif year != current_year:
                maybe_zip("base")
                maybe_zip("odds")
                year = current_year
                maybe_unzip("base", year=year)
                maybe_unzip("odds", year=year)

            with transaction.atomic():
                try:
                    base_df, html_content, base_flg = get_data(url, race_id, driver)
                    result_df, kaisai_date, result_flg = result(url, race_id, "")

                    if html_content == "skip":
                        transaction.set_rollback(True)
                        continue
                    if html_content == "error":
                        transaction.set_rollback(True)
                        raise RuntimeError("race page parse error")

                    if len(base_df) != len(result_df):
                        transaction.set_rollback(True)
                        continue

                    insert_base_db(base_df, username)
                    insert_result_db(result_df, username)

                    if base_flg:
                        name_change(kaisai_date, zip_folder, race_id, "base")
                    if result_flg:
                        name_change(kaisai_date, zip_folder, race_id, "odds")
                except Exception:
                    transaction.set_rollback(True)
                    continue

        maybe_zip("base")
        maybe_zip("odds")
        return "完了"
    finally:
        driver.quit()


@shared_task(bind=True, queue="base_queue", autoretry_for=(), retry_backoff=False, max_retries=0, acks_late=False)
def create_race_task(self, username, start_date_iso, end_date_iso):
    start_date = date.fromisoformat(start_date_iso)
    end_date = date.fromisoformat(end_date_iso)
    pending_pairs = build_pending_race_pairs(start_date, end_date, username)
    return run_base_scrape(self, username, pending_pairs)

@shared_task(bind=True, queue="base_queue", autoretry_for=(), retry_backoff=False, max_retries=0, acks_late=False)
def create_base_task(self, username, url_race_id_pairs):
    return run_base_scrape(self, username, url_race_id_pairs)

@shared_task(bind=True, queue="horse_queue", autoretry_for=(), retry_backoff=False, max_retries=0, acks_late=False)
def create_horse_task(self, username):
    """ [非同期_関数_00]馬履歴情報の取得
        概要：
            ボタン押下時の各イベント
        引数：
            username：ログインユーザー名
        戻り値:
            HttpResponse: 対象画面を選定するフラグ。
    """
    try:
        # 馬履歴情報の取得
        horse_data(self, "html_content", username, "horse")
    except Exception as e:
        print(e)
    
        
    # endregion

@shared_task(queue="jockey_queue", autoretry_for=(), retry_backoff=False, max_retries=0, acks_late=False)
def create_jockey_task(username):
    """
    競馬情報更新

    Parameters:
    ----------
    request : request
        アクセス時、ボタン押下時のRequest情報 

    Returns:
    -------
    render : render
        エラー時に処理中断

    """
    # region "競馬情報更新"
    # データフレーム定義
    zip_folder = settings.MEDIA_ROOT

    try:
        # with transaction.atomic():
        jockey_data("html_content", username, "jockey")
    except Exception as e:
        # transaction.set_rollback(True)
        print(e)
    finally:
        zip_files(zip_folder, "jockey") 


def run_local_race_task(task_id, username, start_date_iso, end_date_iso):
    task = LocalTaskContext(task_id)
    start_date = date.fromisoformat(start_date_iso)
    end_date = date.fromisoformat(end_date_iso)
    pending_pairs = build_pending_race_pairs(start_date, end_date, username)
    return run_base_scrape(task, username, pending_pairs)


def run_local_horse_task(task_id, username):
    task = LocalTaskContext(task_id)
    ensure_media_dirs()
    maybe_unzip("horse", target="horse")
    horse_data(task, "html_content", username, "horse")
    maybe_zip("horse")
    return "完了"


def run_local_jockey_task(task_id, username):
    ensure_media_dirs()
    maybe_unzip("jockey", target="jockey")
    jockey_data("html_content", username, "jockey")
    maybe_zip("jockey")
    return "完了"


def dispatch_race_task(username, start_date_iso, end_date_iso):
    try:
        return create_race_task.apply_async(
            args=[username, start_date_iso, end_date_iso],
            countdown=1,
        )
    except Exception:
        return start_local_task("race", run_local_race_task, username, start_date_iso, end_date_iso)


def dispatch_horse_task(username):
    try:
        return create_horse_task.apply_async(args=[username], countdown=5)
    except Exception:
        return start_local_task("horse", run_local_horse_task, username)


def dispatch_jockey_task(username):
    try:
        return create_jockey_task.apply_async(args=[username], countdown=5)
    except Exception:
        return start_local_task("jockey", run_local_jockey_task, username)
