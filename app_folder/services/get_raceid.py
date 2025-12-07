
# =========================================================
# # 概要       ：レースURLやIDを取得するサービス。
# 改訂履歴      :2025/04/29 初版
# =========================================================

# ライブラリ
import inspect
from urllib import request
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import datetime as datetime_A
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os
from datetime import datetime

# カスタムライブラリ
from django.conf import settings
from ..models import URLMst, WeekEndView
from ..utils.messages import err_messages

# レースURLを取得用クラス
class GetRaceID():
    """ レースURLを取得用クラス
        概要：
            レースURLなどの概要を取得用のクラス。
        引数:
            なし。
        関数:
            __init__():
                インスタンス作成
            create_url_list():
                レースURLなどの概要を取得する。
            calendar_links():
                日単位のカレンダー情報を取得する。
            get_race_ids():
                レース単位のカレンダー情報を取得する。
    """
    # 【インスタンス_00】インスタンス作成
    def __init__(self):
        """ 【インスタンス_00】インスタンス作成
            概要：
                GetRaceIDクラス呼び出し時のインスタンス。
                変数やChromeドライバの初期設定、フォルダの作成を行う。
            戻り値:
                なし。
        """
        # インスタンス変数
        # データ整形時に使用するリスト
        self.dates               = []
        self.race_ids            = []
        self.race_urls           = []
        self.filtered_links      = []
        self.calendar_links_set  = set()

        # 最終的な情報を保持するリスト
        self.final_dates         = []
        self.final_race_ids      = []
        self.final_race_urls     = []

    # 【関数_03】レースIDとレース日の取得
    def get_race_ids(self, url, driver):
        """ 【関数_03】レースIDとレース日の取得
            概要：
                レース日単位のURLからレースIDとレース日の取得
            引数：
                self：インスタンス情報
                url：レース日単位のURL
                driver：Chromeドライバー
            戻り値:
                race_ids: レースIDのリスト
                dates：レース日のリスト
        """
        try:
            # 対象レース情報を保存していれば読み込む
            html_content = ""
            date_format  = datetime.strptime(url[-8:], "%Y%m%d")
            date_format  = date_format.strftime("%Y-%m-%d")
            save_file    = os.path.join(settings.MEDIA_ROOT,"calendar_yyyymmdd", f"{date_format}.html")
            for file in os.listdir(os.path.join(settings.MEDIA_ROOT, "calendar_yyyymmdd")): 
                if date_format in file and file.endswith(".html"):
                    with open(save_file, "r", encoding="EUC-JP", errors="ignore") as file:
                        html_content = file.read()
                        break
                    
            # なければレース日単位のURLにアクセス後、その中にあるレース単位のURLを取得
            if html_content == "":
                time.sleep(1)
                driver.get(url)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "RaceList_DataItem"))
                    )
                except TimeoutException:
                    # タイムアウトエラー
                    print(err_messages("timeout_error", url))
                    return [], []

                # アクセス結果を保存
                html_content = driver.page_source
                with open(save_file, "w", encoding="EUC-JP", errors="ignore") as file:
                    file.write(html_content)

            # 保存ファイルにもアクセスもできない場合、空データを戻り値として返す。
            if not html_content:
                return [], []
            
            # ファイル内容の解析
            soup = BeautifulSoup(html_content, "html.parser")
            race_links = soup.find_all("a", class_="LinkIconRaceMovie")
            date = soup.find("li", class_="Active").get("date")
            date_format = datetime.strptime(date, "%Y%m%d")
            race_cnt = soup.find_all("li", class_="RaceList_DataItem")

            # データがない、または、すでに同じデータが登録されている場合、空データを戻り値として返す。
            if len(race_cnt) == 0:
                return [], []
            elif URLMst.objects.filter(race_date__date=date_format.strftime("%Y-%m-%d")).count() == len(race_cnt):
                return [], []
            
            # アクセス情報からレース日とレースIDを取得する
            for link in race_links:
                match = re.search(r"race/movie.html\?race_id=(\d+)", link["href"])
                if match:
                    if match.group(1) not in self.race_ids:
                        self.race_ids.append(match.group(1))
                        self.dates.append(date)

            return self.race_ids, self.dates

        except Exception as e:
            # システムエラー

            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file=info.filename.split('/')[-1]
            func=info.function
            line=info.lineno
            print(err_messages("system_error", file, "GetRaceID", func, line, e))     
            return "sys_err", "sys_err"

    # 【関数_02】レース日程URLの作成（日単位）
    def calendar_links(self, year, month, start_date_str, end_date_str):
        """ 【関数_02】レース日程URLの作成（日単位）
            概要：
                レース日単位のURLを取得
            引数：
                self：インスタンス情報
                year：ループ処理中の年
                monthループ処理中の月
                start_date_str：開始日付
                end_date_str：終了日付
            戻り値:
                filtered_links: レース日単位のURL
        """
        # 月単位のURLを作成
        html_content = ""
        url          = f"https://race.netkeiba.com/top/calendar.html?year={year}&month={month}"
        start_date   = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date     = datetime.strptime(end_date_str, "%Y-%m-%d")
        save_file    = os.path.join(settings.MEDIA_ROOT,"calendar_yyyymm", f"{year}-{month:02}.html")
        
        try:
            # 指定のファイル情報が保存フォルダにあれば処理を抜ける
            for file in os.listdir(os.path.join(settings.MEDIA_ROOT, "calendar_yyyymm")): 
                if f"{year}-{month:02}" in file and file.endswith(".html"):
                    with open(save_file, "r", encoding="EUC-JP", errors="ignore") as file:
                        html_content = file.read()
                        break
                    
            # ファイル読み込みされていない場合、URLにアクセス
            if html_content == "":
                time.sleep(1)
                req = request.Request(url, headers=settings.HEADERS)
                response =  request.urlopen(req)
                html_content = response.read().decode("EUC-JP", errors="ignore")
                with open(save_file, "w", encoding="EUC-JP", errors="ignore") as file:
                    file.write(html_content)

            # 読み込み、アクセス後データがなければ、戻り値を空で返す
            if not html_content:
                return []

            # HTMLデータがあれば、リンクをフルパスで取得
            soup = BeautifulSoup(html_content, "html.parser")
            links = soup.find_all("a", href=True)
            calendar_links = [link["href"] for link in links if link["href"].startswith("../top/race_list.html?kaisai_date=")]
            full_calendar_links  = [urljoin(url, link) for link in calendar_links]
            
            # 指定期間の対象リンクをリスト形式で戻り値として返す
            for link in full_calendar_links:
                match = re.search(r"kaisai_date=(\d{8})", link)
                if match:
                    race_date_str = match.group(1)
                    race_date = datetime.strptime(race_date_str, "%Y%m%d")
                    if start_date <= race_date <= end_date:
                        self.filtered_links.append(link)
        
            return self.filtered_links

        except Exception as e:
            # システムエラー
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file=info.filename.split('/')[-1]
            func=info.function
            line=info.lineno
            print(err_messages("system_error", file, "GetRaceID", func, line, e))     
            return "sys_err"

    # 【関数_01】URL情報のスクレイピング用
    def create_url_list(self, start, end, driver):
        """ 【関数_01】URL情報のスクレイピング用
            概要：
                URL情報を取得後、URLテーブルに登録する。
            引数：
                self：インスタンス情報
                request：ボタン押下時のpost情報
            戻り値:
                self.final_race_urls：レースURLリスト
                self.final_race_ids：レースIDリスト
                self.final_dates：レース日リスト
        """
        try:
            # 日付を整形
            start_year  = start.year
            start_month = start.month
            start_day   = start.day
            start_date  = start.strftime("%Y-%m-%d")

            end_year    = end.year
            end_month   = end.month
            end_day     = end.day
            end_date    = end.strftime("%Y-%m-%d") 
            # 指定年月日の間でレース日程のURLを取得（日・場所単位）
            for year in range(start_year, end_year + 1):
                for month in range(1, 13):
                    if start_year == end_year and month < start_month:
                        continue
                    elif start_year == end_year and month > end_month:
                        continue
                    elif start_year != end_year and start_year == year and month < start_month:
                        continue
                    elif start_year != end_year and end_year == year and month > end_month:
                        continue
                    
                    # レース日程URLの作成（日単位） 
                    links = self.calendar_links(year, month, start_date, end_date)

                    # システムエラーが発生した場合、処理終了。
                    if links == "sys_err":
                        return "sys_err", "sys_err", "sys_err"
                    links = sorted(links)
                    self.calendar_links_set.update(links)

            # 指定期間内でURLマスタに登録されていないレース日をリストに追加
            race_dates = WeekEndView.objects.filter(
                race_date__gte=datetime_A.date(start_year, start_month, start_day),
                race_date__lte=datetime_A.date(end_year, end_month, end_day)).values("race_date").distinct().order_by("race_date")
            race_date_links    = [f"https://race.netkeiba.com/top/race_list.html?kaisai_date={date["race_date"].strftime("%Y%m%d")}" for date in race_dates]    
            self.calendar_links_set.update(race_date_links)
            self.calendar_links_set = sorted(self.calendar_links_set)

            # 上記までの情報をもとにレースIDとURL(レース単位)を取得
            for calendar_link in self.calendar_links_set:
                race_ids, dates = self.get_race_ids(calendar_link, driver)
                # システムエラーが発生した場合、処理終了。
                if links == "sys_err":
                    return "sys_err", "sys_err", "sys_err"
                if len(race_ids) > 0:
                    self.race_urls = [f"{settings.URL_HEAD}{race_id}" for race_id in race_ids]
                    self.final_race_urls.extend(self.race_urls)
                    self.final_race_ids.extend(race_ids)
                    self.final_dates.extend(dates)

            return self.final_race_urls, self.final_race_ids, self.final_dates

        except Exception as e:
            # システムエラー
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file=info.filename.split('/')[-1]
            func=info.function
            line=info.lineno
            print(err_messages("system_error", file, "GetRaceID", func, line, e))     
            return "sys_err", "sys_err", "sys_err"







