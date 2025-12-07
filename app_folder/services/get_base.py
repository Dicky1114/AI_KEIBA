
# =========================================================
# # 概要       ：レースURLやIDを取得するサービス。
# 改訂履歴      :2025/04/29 初版
# =========================================================

# ライブラリ
import inspect
import pandas as pd
import os
import time
import datetime
from datetime import datetime as datetime1
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.utils.timezone import make_aware
import pytz
from .get_result import result
from .get_horse import horse_data
from .get_jockey import jockey_data
from django.conf import settings
from io import StringIO
import glob

from ..utils.messages import worn_messages, err_messages
# [関数_02]対象のレースIDを含んだファイルが存在するか確認
def find_file_with_race_id(race_id, base_path):
    """ [関数]対象のレースIDを含んだファイルが存在するか確認
        概要：
            対象のレースIDが含まれたファイル名が存在するか確認する。
        引数：
            url：レースURL
            race_id：レースID
            driver：Chromeドライバー
        戻り値:
            files: 対象ファイルパス
    """
    # HTML ファイルかつ race_id を含むものを検索
    pattern = os.path.join(base_path, f"*{race_id}*.html")
    files = glob.glob(pattern)
    return files[0] if files else None

# [関数_01]基本情報のスクレイピング
def get_data(url, race_id, driver):
    """ [関数_01]基本情報のスクレイピング
        概要：
            基本のレース情報をスクレイピングする。
        引数：
            url：レースURL
            race_id：レースID
            driver：Chromeドライバー
        戻り値:
            HttpResponse: 対象画面を選定するフラグ。
    """
    # 変数宣言
    main_retries = 0
    horse_link_df  = pd.DataFrame()
    jockey_link_df  = pd.DataFrame()
    basis_df = pd.DataFrame()
    html_content = ''
    ref_flg = False
    save_file = os.path.join(settings.MEDIA_ROOT,'base', f'{race_id}.html')

    while main_retries < settings.MAX_RETRIES:
        try:
            # ファイル存在チェック
            base_path = os.path.join(settings.MEDIA_ROOT, 'base')
            file_path = find_file_with_race_id(race_id, base_path)

            # 参照ファイルが存在した場合
            if file_path:
                with open(file_path, 'r', encoding='EUC-JP', errors='ignore') as file:
                    html_content = file.read()

            # 参照ファイルが存在しなかった場合
            if html_content == '':
                time.sleep(1)
                driver.get(url)
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "RaceTable01")]')))
                html_content = driver.page_source
                ref_flg = True
                with open(save_file, 'w', encoding='EUC-JP', errors='ignore') as file:
                    file.write(html_content)

            # レース情報をデータフレームに整形
            basis = pd.read_html(StringIO(html_content))
            basis_df = pd.DataFrame(basis[0])
            if basis_df.columns.nlevels > 1:
                basis_df.columns = basis_df.columns.droplevel(1)

            # 確定前のフォーマットの場合、スキップ
            if '予想 オッズ' in basis_df.columns or 'オッズ 更新' in basis_df.columns:
                if os.path.exists(save_file):
                    os.remove(save_file)
                    return "continue", "continue", ref_flg
            # 動的項目のため、オッズ項目が取得できなケースがあり
            elif 'オッズ' not in basis_df.columns:
                if os.path.exists(save_file):
                    os.remove(save_file)
                    raise ValueError(worn_messages("worn_001")) 

            # レース種別フラグ、開催日を取得
            horse_link_df, is_shinba, is_mishori, is_1win, is_2win, is_3win, is_g3, is_g2, is_g1, is_L, is_OP, is_win5, title_text = horse_data("self", html_content, "username", "base")
            jockey_link_df, distance, weather, track_condition, race_place, count = jockey_data(html_content, "username", "base")
            empty_df, kaisai_date, dummy = result(url, race_id, "base") 

            # 列名変更
            basis_df = basis_df[settings.BASE_COL]
            basis_df.rename(columns=settings.NEW_BASE_COL, inplace=True)
            basis_df = basis_df.merge(horse_link_df, on=['horse_name'], how='left')
            basis_df = basis_df.merge(jockey_link_df, on=['jockey_name'], how='left')

            # レース種別等の付与
            kaisai_date = datetime.datetime.strptime(kaisai_date, '%Y%m%d')
            kaisai_date = pytz.timezone("Asia/Tokyo").localize(kaisai_date)
            basis_df['race_id'] = race_id
            basis_df['race_date'] = kaisai_date
            basis_df['new_flg'] = is_shinba
            basis_df['not_win_flg'] = is_mishori
            basis_df['win_1_flg'] = is_1win
            basis_df['win_2_flg'] = is_2win
            basis_df['win_3_flg'] = is_3win
            basis_df['g3_flg'] = is_g3
            basis_df['g2_flg'] = is_g2
            basis_df['g1_flg'] = is_g1
            basis_df['l_flg'] = is_L
            basis_df['op_flg'] = is_OP
            basis_df['is_win5'] = is_win5
            basis_df['event_title'] = title_text
            basis_df['distance'] = str(distance)
            basis_df['weather'] = str(weather)
            basis_df['track_condition'] = str(track_condition)
            basis_df['race_place'] = str(race_place)
            basis_df['count'] = str(count)
            break
        except Exception as e:
            # アクセスできなかった回数をカウントアップ
            main_retries += 1

            # エラー時に作成されたファイルは削除する
            if os.path.exists(save_file):
                os.remove(save_file)

            # オッズが正常に取得できなかった場合
            if isinstance(e, ValueError):
                print(e)
            # システムエラー
            else:
                frame = inspect.currentframe().f_back
                info = inspect.getframeinfo(frame)
                file=info.filename.split('/')[-1]
                func=info.function
                line=info.lineno
                print(err_messages("system_error", file, "None", func, line, e))     
                return "sys_err", "sys_err", "sys_err"

            # ５回以上アクセスエラーとなった場合、次の処理へ進む
            if main_retries == settings.MAX_RETRIES:
                return "sys_err", "sys_err", "sys_err"

    return basis_df, html_content, ref_flg

# endregion
