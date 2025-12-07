
# =========================================================
# # 概要       ：管理画面のメイン処理
# 改訂履歴      :2025/04/29 初版
# =========================================================

# ライブラリ
from pathlib import Path
import inspect
from django.views import View
from django.shortcuts import render
from ..services.get_raceid import GetRaceID
from ..services.insert_db import insert_url_db
from ..utils.zip import unzip_files, zip_files
from django.conf import settings
from ..models import URLMst, CompareView, CreateRaceIDsView
import pandas as pd
from app_folder.admin import admin_site
from selenium import webdriver
from ..forms import GetDataForm
from selenium.webdriver.chrome.options import Options
from ..services.tasks import create_horse_task, create_base_task, create_jockey_task
import os
from django.contrib import messages
from ..utils.messages import info_messages, err_messages

# scraping.html画面用クラス
class ScrapingView(View):
    """ データ取得画面用クラス
        概要：
            競馬情報のスクレイピング、データの登録を担う画面。
        引数:
            View：Djangoのクラスベースビューの親クラス
        関数:
            __init__():
                インスタンス作成
            get():
                初期イベント
    """
    
    # 【インスタンス_00】インスタンス作成
    def __init__(self):
        """ 【インスタンス_00】インスタンス作成
            概要：
                ScrapingViewクラス呼び出し時のインスタンス。
                変数やChromeドライバの初期設定、フォルダの作成を行う。
            戻り値:
                なし。
        """
        # インスタンス変数
        self.race_service = GetRaceID()
        self.d_df = pd.DataFrame()
        self.url_df = pd.DataFrame()
        self.zip_folder = settings.MEDIA_ROOT
        self.url_race_id_pairs = []

        # Chromeドライバ作成
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=self.chrome_options)

        # 保存用フォルダ作成
        if not os.path.exists(settings.MEDIA_ROOT):
            os.makedirs(settings.MEDIA_ROOT)
        if not os.path.exists(f"{settings.MEDIA_ROOT}/base"):
            os.makedirs(f"{settings.MEDIA_ROOT}/base")
        if not os.path.exists(f"{settings.MEDIA_ROOT}/odds"):
            os.makedirs(f"{settings.MEDIA_ROOT}/odds")
        if not os.path.exists(f"{settings.MEDIA_ROOT}/horse"):
            os.makedirs(f"{settings.MEDIA_ROOT}/horse")
        if not os.path.exists(f"{settings.MEDIA_ROOT}/jockey"):
            os.makedirs(f"{settings.MEDIA_ROOT}/jockey")
        if not os.path.exists(f"{settings.MEDIA_ROOT}/calendar_yyyymm"):
            os.makedirs(f"{settings.MEDIA_ROOT}/calendar_yyyymm")
        if not os.path.exists(f"{settings.MEDIA_ROOT}/calendar_yyyymmdd"):
            os.makedirs(f"{settings.MEDIA_ROOT}/calendar_yyyymmdd")
    
    # 【関数_01】URL情報の登録用
    def create_url(self, request, start_date, end_date):
        """ 【関数_01】URL情報の登録用
            概要：
                URL情報を取得後、URLテーブルに登録する。
            引数：
                self：インスタンス情報
                request：ボタン押下時のpost情報
            戻り値:
                date_pair: 対象画面を選定するフラグ。
                date_pairs：
        """
        # 指定期間で登録されていないレース概要を取得
        url_list, race_id_list, dates_list = self.race_service.create_url_list(start_date, end_date, self.driver)

        # システムエラーが発生した場合、処理終了。
        if url_list == "sys_err":
            return "sys_err"
        
        # レース概要をデータフレームに変換
        data = {
            "race_id": race_id_list,
            "race_date": dates_list,
            "url": url_list,
        }
        self.url_df = pd.DataFrame(data)
        self.url_df = self.url_df.drop_duplicates(subset=["race_id", "race_date", "url"])
        self.url_df = self.url_df.sort_values(by="race_date").reset_index(drop=True)

        # レース概要の登録処理
        if insert_url_db(self.url_df, request.user.username) == "sys_err":
            return "sys_err"

        return "success"
        
        # endregion

    # 【GET_00】初期イベント
    def get(self, request):
        """ 【GET_00】初期イベント
            概要：
                scraping.html画面起動時のGetイベント。
            引数：
                self：インスタンス情報
                request：index.htmlから渡されたpost情報
            戻り値:
                HttpResponse: 対象画面を選定するフラグ。
        """
        # 日付フォームを取得
        form = GetDataForm()
        context = admin_site.each_context(request)  # ★これが超重要
        data_type = request.GET.get("type")
        context.update({
            "form": form,
            "data_type": data_type,
        })

        # 1. レース情報ボタン押下時
        if data_type == "race":
            context["data_type"] = "race"
        # 2. 馬のレース履歴ボタン押下時
        elif data_type == "horse":
            context["data_type"] = "horse"
        # 3. 騎手のレース履歴ボタン押下時
        elif data_type == "jockey":
            context["data_type"] = "jockey"
        # 4. 学習データへの反映ボタン押下時
        elif data_type == "apply":
            context["data_type"] = "apply"
        else:
            # どれにも当てはまらない場合、画面遷移しない
            return render(request, "admin/index.html")
        
        # 対象画面に遷移
        return render(request, "admin/scraping.html", context)
   
    # 【POST_00】ボタン押下イベント
    def post(self, request):
        """ 【POST_00】ボタン押下イベント
            概要：
                ボタン押下時の各イベント
            引数：
                self：インスタンス情報
                request：ボタン押下時のpost情報
            戻り値:
                HttpResponse: 対象画面を選定するフラグ。
        """
        try:
            # post情報を取得
            form = GetDataForm(request.POST)
            data_type = request.GET.get("type") 

            # post情報の検証
            if form.is_valid():
                if form.cleaned_data["start_date"] and form.cleaned_data["end_date"]:
                    start_date  = form.cleaned_data["start_date"]
                    end_date    = form.cleaned_data["end_date"]
                else:
                    start_date = "None"
                    end_date = "None"
                
                # 1. レース情報（URL、レース、結果）のスクレイピング
                if data_type == "race":
                    messages.info(request, info_messages("info_001","レースURLの作成処理"))
                    # 保存データの解凍
                    cnt_ym = len([f for f in os.listdir(os.path.join(f"{settings.MEDIA_ROOT}/calendar_yyyymm")) if f.endswith(".zip")])
                    cnt_ymd = len([f for f in os.listdir(os.path.join(f"{settings.MEDIA_ROOT}/calendar_yyyymmdd")) if f.endswith(".zip")])
                    if cnt_ym > 0:
                        unzip_files(None, self.zip_folder, "calendar_yyyymm", "")
                        if cnt_ymd > 0:
                            unzip_files(None, self.zip_folder, "calendar_yyyymmdd", "")

                    # URL情報の取得
                    if self.create_url(request, start_date, end_date) == "sys_err":
                        messages.error(request, err_messages("error_001","URLの作成処理"))
                        return render(request, "admin/scraping.html")
                    else:
                        messages.info(request, info_messages("info_002","レースURLの作成処理"))
                        
                    # レース情報、結果情報にないレースIDを取得
                    messages.info(request, info_messages("info_001","レース情報スクレイピング処理"))
                    self.url_race_id_pairs = URLMst.objects.exclude(
                        race_id__in=CompareView.objects.values("race_id")
                    ).order_by("race_id").values_list("url", "race_id")

                    # 12レースない日程は、再度そのレース日を取り直すため、対象データ取得後、リストを合体
                    race_id_url_pairs = CreateRaceIDsView.objects.exclude(race_id__in=["202404030612", "202408060108"]).values_list("url", "race_id")
                    url_race_id_pairs_tran = sorted(
                        list(self.url_race_id_pairs) + list(race_id_url_pairs),
                        key=lambda x: x[1]
                    )
                    print(race_id_url_pairs)
                    # 本処理の中でドライバーを使用するため、一度解除
                    self.driver.quit()
                    print("非同期処理")
                    task = create_base_task.apply_async(args=[request.user.username, url_race_id_pairs_tran ], countdown=5)
                    return render(request, "admin/scraping.html", {"form": form, "data_type": "race", "task_id": task.id})
                return render(request, "admin/scraping.html", {"data_type": data_type, "form": form})
            else:
                # 2. 馬のレース履歴の取得
                if data_type == "horse":
                    # 馬のレース履歴の取得
                    self.driver.quit()
                    print(info_messages("info_001", "2. 馬のレース履歴の取得（非同期処理）"))
                    unzip_files(None, self.zip_folder, "horse", "horse")
                    task = create_horse_task.apply_async(args=[request.user.username], countdown=5)
                    print(info_messages("info_002", "2. 馬のレース履歴の取得（非同期処理）"))
                    messages.success(request, info_messages("info_003","2. 馬のレース履歴のスクレイピング"))
                    return render(request, "admin/scraping.html", {"form": form, "data_type": "horse", "task_id": task.id})
                elif data_type == "jockey":
                    # 騎手のレース履歴の取得
                    self.driver.quit()
                    print(info_messages("info_001", "3. 騎手のレース履歴の取得（非同期処理）"))
                    # zip_files(self.zip_folder, "jockey") 
                    unzip_files(None, self.zip_folder, "jockey", "jockey")
                    create_jockey_task.apply_async(args=[request.user.username], countdown=5)
                    print(info_messages("info_002", "3. 騎手のレース履歴の取得（非同期処理）"))
                    messages.success(request, info_messages("info_003", "3. 騎手のレース履歴の取得が完了しました。"))
                    return render(request, "admin/scraping.html")
                else:
                    return render(request, "admin/scraping.html", {"data_type": data_type, "form": form})
        except Exception as e:
            # システムエラー
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file=info.filename.split('/')[-1]
            func=info.function
            line=info.lineno
            print(err_messages("system_error", file, "GetRaceID", func, line, e))     
            messages.error(request, err_messages("error_000"))
            return render(request, "admin/scraping.html")
        finally:
            # 処理の最後に対象フォルダがZip化されていない場合、圧縮する
            # レース情報格納ファイルのZip化
            if data_type == "race":
                if any(p.is_file() for p in Path(os.path.join(f'{settings.MEDIA_ROOT}/calendar_yyyymm')).iterdir()): 
                    ym_html_cnt = len([f for f in os.listdir(os.path.join(f'{settings.MEDIA_ROOT}/calendar_yyyymm')) if f.endswith('.html')])
                    if ym_html_cnt > 0:
                        zip_files(self.zip_folder, "calendar_yyyymm")
                if any(p.is_file() for p in Path(os.path.join(f'{settings.MEDIA_ROOT}/calendar_yyyymmdd')).iterdir()): 
                    ymd_html_cnt = len([f for f in os.listdir(os.path.join(f'{settings.MEDIA_ROOT}/calendar_yyyymmdd')) if f.endswith('.html')])
                    if ymd_html_cnt > 0:
                        zip_files(self.zip_folder, "calendar_yyyymmdd")
                if any(p.is_file() for p in Path(os.path.join(f'{settings.MEDIA_ROOT}/base')).iterdir()): 
                    base_html_cnt = len([f for f in os.listdir(os.path.join(f'{settings.MEDIA_ROOT}/base')) if f.endswith('.html')])
                    if base_html_cnt > 0:
                        zip_files(self.zip_folder, "odds")
                if any(p.is_file() for p in Path(os.path.join(f'{settings.MEDIA_ROOT}/odds')).iterdir()): 
                    base_html_cnt = len([f for f in os.listdir(os.path.join(f'{settings.MEDIA_ROOT}/odds')) if f.endswith('.html')])
                    if base_html_cnt > 0:
                        zip_files(self.zip_folder, "odds")
            # 馬情報格納ファイルのZip化
            elif data_type == "horse":
                if any(p.is_file() for p in Path(os.path.join(f'{settings.MEDIA_ROOT}/horse')).iterdir()): 
                    horse_html_cnt = len([f for f in os.listdir(os.path.join(f'{settings.MEDIA_ROOT}/horse')) if f.endswith('.html')])
                    if horse_html_cnt > 0:
                        zip_files(self.zip_folder, "horse")
            # 騎手情報格納ファイルのZip化
            elif data_type == "jockey":
                if any(p.is_file() for p in Path(os.path.join(f'{settings.MEDIA_ROOT}/jockey')).iterdir()): 
                    horse_html_cnt = len([f for f in os.listdir(os.path.join(f'{settings.MEDIA_ROOT}/jockey')) if f.endswith('.html')])
                    if horse_html_cnt > 0:
                        zip_files(self.zip_folder, "jockey")



scraping_view = ScrapingView.as_view()