"""
分析 API URL設定
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# TODO: 後でViewSetを追加

urlpatterns = [
    path('', include(router.urls)),
]
