from django.http import JsonResponse
from celery.result import AsyncResult
from ..services.tasks import (
    get_redis_client,
    local_task_exists,
    read_local_task_state,
    set_local_task_stop,
)

def task_status(request, task_id):
    if local_task_exists(task_id):
        return JsonResponse(read_local_task_state(task_id) or {"task_id": task_id, "state": "PENDING", "status": "PENDING"})

    task_result = AsyncResult(task_id)
    info = task_result.info if isinstance(task_result.info, dict) else {}
    response = {
        'task_id': task_id,
        'state': task_result.state,
        'status': task_result.state,
        'result': task_result.result if isinstance(task_result.result, str) else None,
        'details': info,
        'current': info.get('current', 0),
        'total': info.get('total', 0),
        'progress': info.get('current', 0),
    }
    return JsonResponse(response)

# 停止用ビュー
def stop_task(request, task_id):
    if local_task_exists(task_id):
        set_local_task_stop(task_id)
        return JsonResponse({"message": "停止フラグをセットしました"})

    redis_client = get_redis_client()
    if not redis_client:
        return JsonResponse({"message": "Redis is not configured"}, status=503)

    try:
        redis_client.set(f"stop:{task_id}", 1, ex=60 * 60)
    except Exception:
        return JsonResponse({"message": "Redis stop flag could not be set"}, status=503)
    return JsonResponse({"message": "停止フラグをセットしました"})
