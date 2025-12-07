
# =========================================================
# # 概要       ：管理画面のメイン処理
# 改訂履歴      :2025/04/29 初版
# =========================================================

# ライブラリ
from django.views import View
from django.shortcuts import render
from ..services.get_raceid import GetRaceID
from ..services.insert_db import insert_url_db
from ..utils.zip import unzip_files, zip_files
from django.conf import settings
import pandas as pd
import inspect
from selenium import webdriver
from ..forms import GetDataForm, TrainForm
from selenium.webdriver.chrome.options import Options
from ..services.tasks import create_horse_task, create_base_task, create_jockey_task
import os
from django.contrib import messages
from ..utils.messages import info_messages, err_messages
from django.utils.timezone import localtime, now
import csv
from django.http import HttpResponse
from django.utils.timezone import now
from ..models import TrainingInfo





# scraping.html画面用クラス
class  TrainingView(View):
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
        form = TrainForm()
        data_type = request.GET.get("type")
        context = {
            "form": form,
            "data_type": data_type,
        }
        
        return render(request, "admin/training.html", context)
   
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
            form = TrainForm(request.POST)
            data_type = request.GET.get("type") 
            # post情報の検証
            if form.is_valid():
                basic_cols = request.POST.getlist("race_basic")
                horse_cols = request.POST.getlist("past_horse")
                jockey_cols = request.POST.getlist("past_jockey")
                result_cols = request.POST.getlist("result_info")
                if form.cleaned_data["start_date"] and form.cleaned_data["end_date"]:
                    start_date  = form.cleaned_data["start_date"]
                    end_date    = form.cleaned_data["end_date"]
                else:
                    start_date = None
                    end_date = None
                
                # 1. レース情報（URL、レース、結果）のスクレイピング
                if data_type == "train":
                    messages.info(request, info_messages("info_001","レースURLの作成処理"))
                    selected_columns = [col for col in basic_cols + horse_cols + jockey_cols + result_cols if col not in ["select_all_basic", "select_all_horse", "select_all_jockey", "select_all_result"]]

                    selected_columns.insert(0, "id")
                    queryset = TrainingInfo.objects.all()
                    if start_date != "None" and end_date != "None":
                        queryset = queryset.filter(today_race_date__range=[start_date, end_date])
                    else:
                        queryset = queryset

                    # CSV出力先の絶対パス
                    csv_dir = os.path.join(settings.MEDIA_ROOT, "csv_export")
                    os.makedirs(csv_dir, exist_ok=True)
                    csv_name = f"train_data_{localtime(now()).strftime("%Y%m%d_%H%M%S")}.csv"
                    csv_path = os.path.join(csv_dir, csv_name)
                    from django.forms.models import model_to_dict

                    with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
                        writer = csv.DictWriter(f, fieldnames=selected_columns)
                        writer.writeheader()
                        for idx, row in enumerate(queryset, start = 1):
                            row_dict = model_to_dict(row)
                            output_row = {k: row_dict.get(k, "") for k in selected_columns if k != "row_id"}
                            output_row["id"] = idx 
                            writer.writerow(output_row)

                    context = {
                        "form": form,
                        "data_type": data_type,
                        "selected_basic": basic_cols,
                        "selected_horse": horse_cols,
                        "selected_jockey": jockey_cols,
                        "selected_result": result_cols,
                    }
                    messages.success(request, f"CSVファイルを出力しました：{csv_path}")
                    return render(request, "admin/training.html", context)
            else:
                # 2. 馬のレース履歴の取得
                if data_type == "train":
                    # 馬のレース履歴の取得
                    self.driver.quit()
                    print(info_messages("info_001", "2. 馬のレース履歴の取得（非同期処理）"))
                    unzip_files(None, self.zip_folder, "horse", "horse")
                    task = create_horse_task.apply_async(args=[request.user.username], countdown=5)
                    print(info_messages("info_002", "2. 馬のレース履歴の取得（非同期処理）"))
                    messages.success(request, info_messages("info_003","2. 馬のレース履歴のスクレイピング"))
                    return render(request, "admin/scraping.html", {"form": form, "data_type": "horse", "task_id": task.id})
                else:
                    return render(request, "admin/scraping.html", {"data_type": data_type, "form": form})
        except Exception as e:
            # システムエラー
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file=info.filename.split("/")[-1]
            func=info.function
            line=info.lineno
            print(err_messages("system_error", file, "GetRaceID", func, line, e))     
            messages.error(request, err_messages("error_000"))
            return render(request, "admin/scraping.html")
        finally:
            # 処理の最後に対象フォルダがZip化されていない場合、圧縮する
            # レース情報格納ファイルのZip化
            if data_type == "train":
                print("aaa")
            # 騎手情報格納ファイルのZip化
            else:
                print("bbb")

training_view = TrainingView.as_view()