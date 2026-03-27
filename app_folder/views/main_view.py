
# =========================================================
# 概要       ：統合メインビュー（認証不要・シングルユーザー）
# =========================================================

from django.views import View
from django.shortcuts import render
from django.conf import settings
from django.contrib import messages
from django.utils.timezone import localtime, now
from datetime import datetime, timedelta
import pandas as pd
import os
import csv
import inspect

from ..forms import GetDataForm, TrainForm
from ..models import URLMst, CompareView, CreateRaceIDsView, TrainingInfo
from ..services.get_raceid import GetRaceID
from ..services.insert_db import insert_url_db
from ..services.tasks import create_horse_task, create_jockey_task, create_race_task
from ..utils.zip import unzip_files, zip_files
from ..utils.messages import info_messages, err_messages

SYSTEM_USER = "admin"  # シングルユーザーモード用


def _ensure_media_dirs():
    for subdir in ["", "/base", "/odds", "/horse", "/jockey", "/calendar_yyyymm", "/calendar_yyyymmdd"]:
        os.makedirs(f"{settings.MEDIA_ROOT}{subdir}", exist_ok=True)


class MainView(View):

    def get(self, request):
        today = datetime.today().date()
        today_minus30 = (datetime.today() - timedelta(days=30)).date()
        context = {
            "scraping_form": GetDataForm(),
            "train_form": TrainForm(),
            "today": today,
            "today_minus30": today_minus30,
            "active_tab": "data",
        }
        return render(request, "main.html", context)

    def post(self, request):
        action = request.GET.get("action") or request.POST.get("action")
        today = datetime.today().date()
        today_minus30 = (datetime.today() - timedelta(days=30)).date()
        base_context = {
            "scraping_form": GetDataForm(),
            "train_form": TrainForm(),
            "today": today,
            "today_minus30": today_minus30,
            "active_tab": "data",
        }

        # ────────────────────────────────────────
        # 1. レース情報スクレイピング
        # ────────────────────────────────────────
        if action == "race":
            form = GetDataForm(request.POST)
            base_context["scraping_form"] = form
            if not form.is_valid():
                messages.error(request, "日付を正しく入力してください。")
                return render(request, "main.html", base_context)

            try:
                start_date = form.cleaned_data["start_date"]
                end_date = form.cleaned_data["end_date"]
                task = create_race_task.apply_async(
                    args=[SYSTEM_USER, start_date.isoformat(), end_date.isoformat()],
                    countdown=1,
                )
                base_context["task_id"] = task.id
                messages.success(request, "レーススクレイピングを開始しました。")

            except Exception as e:
                messages.error(request, f"エラーが発生しました: {e}")

            return render(request, "main.html", base_context)

        # ────────────────────────────────────────
        # 2. 馬のレース履歴
        # ────────────────────────────────────────
        elif action == "horse":
            try:
                _ensure_media_dirs()
                unzip_files(None, settings.MEDIA_ROOT, "horse", "horse")
                task = create_horse_task.apply_async(args=[SYSTEM_USER], countdown=5)
                base_context["task_id"] = task.id
                messages.success(request, "馬のレース履歴スクレイピングを開始しました。")
            except Exception as e:
                messages.error(request, f"エラーが発生しました: {e}")
            return render(request, "main.html", base_context)

        # ────────────────────────────────────────
        # 3. 騎手のレース履歴
        # ────────────────────────────────────────
        elif action == "jockey":
            try:
                _ensure_media_dirs()
                unzip_files(None, settings.MEDIA_ROOT, "jockey", "jockey")
                task = create_jockey_task.apply_async(args=[SYSTEM_USER], countdown=5)
                base_context["task_id"] = task.id
                messages.success(request, "騎手のレース履歴スクレイピングを開始しました。")
            except Exception as e:
                messages.error(request, f"エラーが発生しました: {e}")
            return render(request, "main.html", base_context)

        # ────────────────────────────────────────
        # 4. CSV 出力（学習データ）
        # ────────────────────────────────────────
        elif action == "train":
            form = TrainForm(request.POST)
            base_context["train_form"] = form
            base_context["active_tab"] = "train"
            if form.is_valid():
                basic_cols = request.POST.getlist("race_basic")
                horse_cols = request.POST.getlist("past_horse")
                jockey_cols = request.POST.getlist("past_jockey")
                result_cols = request.POST.getlist("result_info")
                start_date = form.cleaned_data.get("start_date")
                end_date = form.cleaned_data.get("end_date")

                skip = {"select_all_basic", "select_all_horse", "select_all_jockey", "select_all_result"}
                selected = [c for c in basic_cols + horse_cols + jockey_cols + result_cols if c not in skip]
                selected.insert(0, "id")

                queryset = TrainingInfo.objects.all()
                if start_date and end_date:
                    queryset = queryset.filter(today_race_date__range=[start_date, end_date])

                csv_dir = os.path.join(settings.MEDIA_ROOT, "csv_export")
                os.makedirs(csv_dir, exist_ok=True)
                csv_name = f"train_data_{localtime(now()).strftime('%Y%m%d_%H%M%S')}.csv"
                csv_path = os.path.join(csv_dir, csv_name)

                from django.forms.models import model_to_dict
                with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=selected)
                    writer.writeheader()
                    for idx, row in enumerate(queryset, start=1):
                        row_dict = model_to_dict(row)
                        out = {k: row_dict.get(k, "") for k in selected if k != "row_id"}
                        out["id"] = idx
                        writer.writerow(out)

                messages.success(request, f"CSVを出力しました: {csv_path}")
            else:
                messages.error(request, "入力内容を確認してください。")

            return render(request, "main.html", base_context)

        return render(request, "main.html", base_context)


main_view = MainView.as_view()
