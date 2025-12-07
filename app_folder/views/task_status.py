from django.http import JsonResponse
from celery.result import AsyncResult
from django.contrib import messages
from ..utils.messages import info_messages, err_messages

def task_status(request, task_id):
    task_result = AsyncResult(task_id)
    response = {
        'status': task_result.status,
        'result': task_result.result,
        'task_id': task_id
    }
    if task_result.status  == "SUCCESS":
        messages.info(request, info_messages("info_002","レース情報スクレイピング処理"))

    return JsonResponse(response)

# 停止用ビュー
def stop_task(request, task_id):
    r.set(f"stop:{task_id}", 1)
    return JsonResponse({"message": "停止フラグをセットしました"})
