from celery import shared_task
from celery_progress.backend import ProgressRecorder
import random
from ..services.get_base import get_data
from ..services.get_horse import horse_data
from ..services.get_jockey import jockey_data
from ..services.get_result import result
from ..services.insert_db import insert_base_db, insert_result_db
from ..utils.zip import name_change
import pandas as pd
import os
from django.db import transaction
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from ..utils.zip import unzip_files, zip_files, name_change
from celery import shared_task
import redis
from django.contrib import messages
from ..utils.messages import info_messages, err_messages

def set_user_agent(driver, user_agent):
    """ブラウザのUser-Agentを変更する"""
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": user_agent
})

def change_user_agent(driver, user_agents):
    random_user_agent = random.choice(user_agents)
    set_user_agent(driver, random_user_agent)
    return driver

@shared_task(bind=True, queue="base_queue", autoretry_for=(), retry_backoff=False, max_retries=0, acks_late=False)
def create_base_task(self, username, url_race_id_pairs):
    """ [非同期_関数_00]レース履歴情報の取得
        概要：
            レース情報を取得する非同期処理
        引数：
            username：ログインユーザー名
            url_race_id_pairs：URLとレースIDのペアリスト
        戻り値:
            HttpResponse: 対象画面を選定するフラグ。
    """
    # 変数宣言
    r = redis.StrictRedis()
    progress_recorder = ProgressRecorder(self)
    base_df= pd.DataFrame()
    result_df = pd.DataFrame()
    zip_folder = settings.MEDIA_ROOT
    year = None

    # Chromeドライバーの設定
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        total = len(url_race_id_pairs)
        for i, (url, race_id) in enumerate(url_race_id_pairs):
            if r.get(f"stop:{self.request.id}"):
                messages.info(self.request, info_messages("info_002","レース情報スクレイピング処理（停止処理）"))
                zip_files(zip_folder, "base")
                zip_files(zip_folder, "odds") 
                return "停止しました。"
            
            # プログレスバー設定
            progress_recorder.set_progress(i + 1, total, f"{i+1}/{total} 件 処理中...")

            # User-Agentの切り替え
            driver = change_user_agent(driver, settings.USER_AGENTS)
            
            # 参照ファイル解凍（年単位）
            if year == None:
                year = race_id[:4]
                base_cnt = len([f for f in os.listdir(os.path.join(f"{settings.MEDIA_ROOT}/base")) if str(year) in f and f.endswith(".zip")])
                odds_cnt = len([f for f in os.listdir(os.path.join(f"{settings.MEDIA_ROOT}/odds")) if str(year) in f and f.endswith(".zip")])
                if base_cnt > 0:
                    unzip_files(year, zip_folder, "base", None)
                if odds_cnt > 0:
                    unzip_files(year, zip_folder, "odds", None)

            # 年が切り替わったタイミングの処理
            elif year != race_id[:4]:
                year = race_id[:4]
                zip_files(zip_folder, "base")
                zip_files(zip_folder, "odds") 
                base_cnt = len([f for f in os.listdir(os.path.join(f"{settings.MEDIA_ROOT}/base")) if str(year) in f and f.endswith(".zip")])
                odds_cnt = len([f for f in os.listdir(os.path.join(f"{settings.MEDIA_ROOT}/odds")) if str(year) in f and f.endswith(".zip")])
                if base_cnt > 0:
                    unzip_files(year, zip_folder, "base", None)
                if odds_cnt > 0:
                    unzip_files(year, zip_folder, "odds", None)

            # メイン登録処理
            with transaction.atomic():
                try:
                    # 基本・結果情報の取得
                    base_df, html_content, base_flg = get_data(url, race_id, driver)
                    result_df, kaisai_date, result_flg  = result(url, race_id, "")
                    
                    # 当日データなどデータが完全でない場合、次のURLにアクセス
                    if html_content == "skip":
                        transaction.set_rollback(True)
                        continue
                    elif html_content == "error":
                        transaction.set_rollback(True)
                        raise Exception("error_messages")

                    # データベース更新
                    if len(base_df) == len(result_df):
                        insert_base_db(base_df, username)
                        insert_result_db(result_df, username)
                        if base_flg == True:
                            print("URL読込【Base】")
                            name_change(kaisai_date, zip_folder, race_id, "base")
                        else:
                            print("ファイル読込【Base】")

                        if result_flg == True:
                            print("URL読込【Result】")
                            name_change(kaisai_date, zip_folder, race_id, "odds")
                        else:
                            print("ファイル読込【Result】")

                    else:
                        # 基本情報と結果情報の頭数が異なる場合
                        print("データ数が異なります。")
                        transaction.set_rollback(True)
                        continue
                except Exception as e:
                    print(e)
                    transaction.set_rollback(True)
                    continue
        
    finally:
        # 保存ファイルを圧縮
        
        driver.quit()
    # endregion

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
        # transaction.set_rollback(True)
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
        
    # endregion
