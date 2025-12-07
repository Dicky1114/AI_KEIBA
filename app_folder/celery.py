# horse/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Djangoの設定モジュールを設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.base')

app = Celery('horse')

# Celeryの設定をDjangoの設定ファイルから読み込む
app.config_from_object('django.conf:settings', namespace='CELERY')

# タスクモジュールの自動検出
app.autodiscover_tasks()
