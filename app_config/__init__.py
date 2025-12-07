from __future__ import absolute_import, unicode_literals

# Celeryの設定
import os
from celery import Celery

# Djangoの設定モジュールを設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.base')

# Celeryのインスタンスを作成
app = Celery('app_config')

# Djangoの設定をCeleryに読み込ませる
app.config_from_object('django.conf:settings', namespace='CELERY')

# タスクの自動発見
app.autodiscover_tasks()