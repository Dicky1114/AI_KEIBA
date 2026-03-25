
# =========================================================
# 概要：売上・案件管理 API ビュー（JSON）
# =========================================================

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from ..models import SalesProject


def _project_to_dict(p):
    return {
        "id":               p.id,
        "entry_month":      p.entry_month.strftime("%Y-%m") if p.entry_month else "",
        "cl_name":          p.cl_name,
        "project_name":     p.project_name,
        "sales_amount":     int(p.sales_amount),
        "outsource_amount": int(p.outsource_amount),
        "gross_profit":     int(p.gross_profit),
        "gross_profit_rate": float(p.gross_profit_rate),
        "status":           p.status,
        "status_label":     p.get_status_display(),
        "memo":             p.memo,
    }


def _parse_decimal(val):
    try:
        return Decimal(str(val).replace(",", "").replace("¥", "").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


# ─── 一覧 + 月次サマリ ───────────────────────────────────────────────────────
@require_http_methods(["GET"])
def sales_list(request):
    projects = SalesProject.objects.all()

    # フィルタ: ステータス
    status = request.GET.get("status")
    if status:
        projects = projects.filter(status=status)

    # フィルタ: 年月範囲
    from_month = request.GET.get("from_month")
    to_month   = request.GET.get("to_month")
    if from_month:
        projects = projects.filter(entry_month__gte=from_month + "-01")
    if to_month:
        projects = projects.filter(entry_month__lte=to_month + "-28")

    project_list = [_project_to_dict(p) for p in projects]

    # 月次集計（グラフ用）
    monthly = (
        SalesProject.objects.exclude(entry_month=None)
        .values("entry_month")
        .annotate(
            total_sales=Sum("sales_amount"),
            total_gross=Sum("gross_profit"),
            total_outsource=Sum("outsource_amount"),
        )
        .order_by("entry_month")
    )
    monthly_list = [
        {
            "month":         m["entry_month"].strftime("%Y/%m"),
            "sales":         int(m["total_sales"] or 0),
            "gross":         int(m["total_gross"] or 0),
            "outsource":     int(m["total_outsource"] or 0),
        }
        for m in monthly
    ]

    # KPI集計
    totals = SalesProject.objects.aggregate(
        total_sales=Sum("sales_amount"),
        total_gross=Sum("gross_profit"),
        total_outsource=Sum("outsource_amount"),
        deal_count=Count("id"),
    )

    return JsonResponse({
        "projects":  project_list,
        "monthly":   monthly_list,
        "totals": {
            "sales":         int(totals["total_sales"] or 0),
            "gross":         int(totals["total_gross"] or 0),
            "outsource":     int(totals["total_outsource"] or 0),
            "deal_count":    totals["deal_count"] or 0,
        },
    })


# ─── 新規追加 / 編集 ─────────────────────────────────────────────────────────
@require_http_methods(["POST"])
def sales_upsert(request):
    data = request.POST
    project_id = data.get("id")

    entry_month_raw = data.get("entry_month", "").strip()
    entry_month = None
    if entry_month_raw:
        for fmt in ("%Y-%m", "%Y/%m", "%Y%m"):
            try:
                entry_month = datetime.strptime(entry_month_raw, fmt).date().replace(day=1)
                break
            except ValueError:
                continue

    fields = {
        "entry_month":       entry_month,
        "cl_name":           data.get("cl_name", "").strip(),
        "project_name":      data.get("project_name", "").strip(),
        "sales_amount":      _parse_decimal(data.get("sales_amount", "0")),
        "outsource_amount":  _parse_decimal(data.get("outsource_amount", "0")),
        "status":            data.get("status", "negotiating"),
        "memo":              data.get("memo", ""),
    }

    if not fields["cl_name"] or not fields["project_name"]:
        return JsonResponse({"ok": False, "error": "CL名・案件名は必須です"}, status=400)

    if project_id:
        try:
            p = SalesProject.objects.get(pk=project_id)
            for k, v in fields.items():
                setattr(p, k, v)
            p.save()
            return JsonResponse({"ok": True, "project": _project_to_dict(p)})
        except SalesProject.DoesNotExist:
            return JsonResponse({"ok": False, "error": "案件が見つかりません"}, status=404)
    else:
        p = SalesProject(**fields)
        p.save()
        return JsonResponse({"ok": True, "project": _project_to_dict(p)})


# ─── 削除 ────────────────────────────────────────────────────────────────────
@require_http_methods(["POST"])
def sales_delete(request, project_id):
    try:
        SalesProject.objects.get(pk=project_id).delete()
        return JsonResponse({"ok": True})
    except SalesProject.DoesNotExist:
        return JsonResponse({"ok": False, "error": "案件が見つかりません"}, status=404)


# ─── CSV インポート ──────────────────────────────────────────────────────────
@require_http_methods(["POST"])
def sales_import(request):
    f = request.FILES.get("csv_file")
    if not f:
        return JsonResponse({"ok": False, "error": "ファイルが選択されていません"}, status=400)

    try:
        content = f.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))

        # ヘッダ候補マッピング
        HEADER_MAP = {
            "cl_name":           ["CL名", "cl_name", "クライアント", "顧客名"],
            "project_name":      ["案件名", "project_name", "プロジェクト名"],
            "entry_month":       ["入金月", "entry_month", "月"],
            "sales_amount":      ["売上", "sales_amount", "売上金額", "受注金額"],
            "outsource_amount":  ["外注費", "outsource_amount", "外注金額", "外注支払額"],
            "status":            ["ステータス", "status"],
            "memo":              ["メモ", "memo", "備考"],
        }

        STATUS_LABEL_MAP = {
            "商談中": "negotiating", "negotiating": "negotiating",
            "受注済": "ordered",     "ordered":     "ordered",
            "進行中": "in_progress", "in_progress": "in_progress",
            "完了":   "completed",   "completed":   "completed",
            "失注":   "lost",        "lost":        "lost",
        }

        headers = reader.fieldnames or []

        def find_col(key):
            for candidate in HEADER_MAP.get(key, []):
                if candidate in headers:
                    return candidate
            return None

        col = {k: find_col(k) for k in HEADER_MAP}

        created = 0
        errors  = []

        for i, row in enumerate(reader, start=2):
            cl   = (row.get(col["cl_name"], "") or "").strip()
            proj = (row.get(col["project_name"], "") or "").strip()
            if not cl and not proj:
                continue

            entry_month = None
            if col["entry_month"]:
                raw = (row.get(col["entry_month"], "") or "").strip()
                for fmt in ("%Y-%m", "%Y/%m", "%Y%m", "%Y年%m月"):
                    try:
                        entry_month = datetime.strptime(raw, fmt).date().replace(day=1)
                        break
                    except ValueError:
                        continue

            status_raw = (row.get(col["status"], "") or "").strip() if col["status"] else ""
            status = STATUS_LABEL_MAP.get(status_raw, "negotiating")

            try:
                p = SalesProject(
                    entry_month      = entry_month,
                    cl_name          = cl or "(未設定)",
                    project_name     = proj or "(未設定)",
                    sales_amount     = _parse_decimal(row.get(col["sales_amount"], "0") if col["sales_amount"] else "0"),
                    outsource_amount = _parse_decimal(row.get(col["outsource_amount"], "0") if col["outsource_amount"] else "0"),
                    status           = status,
                    memo             = (row.get(col["memo"], "") or "").strip() if col["memo"] else "",
                )
                p.save()
                created += 1
            except Exception as e:
                errors.append(f"行{i}: {e}")

        return JsonResponse({"ok": True, "created": created, "errors": errors})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
