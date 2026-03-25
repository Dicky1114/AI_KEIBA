"""
URL configuration for app_config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app_folder.views.task_status import task_status, stop_task
from app_folder.admin import admin_site
from app_folder.views.main_view import main_view
from app_folder.views.sales_view import sales_list, sales_upsert, sales_delete, sales_import

# URLの全体設計
urlpatterns = [
    # ルート → 統合ダッシュボード（認証不要）
    path('', main_view, name='main'),
    # 管理画面（データ管理用）
    path('admin/', admin_site.urls),
    # Celery タスク状態確認・停止
    path("chesck_task_status/<str:task_id>/", task_status, name="task_status"),
    path('stop_task/<uuid:task_id>/', stop_task, name='stop_task'),
    # 売上・案件管理 API
    path('sales/list/',           sales_list,   name='sales_list'),
    path('sales/upsert/',         sales_upsert, name='sales_upsert'),
    path('sales/delete/<int:project_id>/', sales_delete, name='sales_delete'),
    path('sales/import/',         sales_import, name='sales_import'),
]

# メディアファイル公開用のURL設定
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

