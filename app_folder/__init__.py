# app_folder/__init__.py
from __future__ import absolute_import, unicode_literals

# Djangoが起動する際に、Celeryインスタンスを起動するようにする
from .celery import app as celery_app

__all__ = ('celery_app',)
