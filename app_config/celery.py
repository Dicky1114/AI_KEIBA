from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Django の設定モジュールを指定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_folder.settings')

# Celery アプリケーションの作成
app = Celery('app_folder')

# Django の設定ファイルから Celery 設定を読み込む
app.config_from_object('django.conf:settings', namespace='CELERY')

# タスクを自動的に発見
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
