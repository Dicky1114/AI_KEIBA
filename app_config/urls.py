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

# URLの全体設計
urlpatterns = [
    # 今回作成するアプリ「app_folder」にアクセスするURL
	path('accounts/', include('accounts.urls')),
    # path('admin/', admin.site.urls),
    path('admin/', admin_site.urls), 
    path("chesck_task_status/<str:task_id>/", task_status, name="task_status"),
    path('stop_task/<uuid:task_id>/', stop_task, name='stop_task'),
]

# メディアファイル公開用のURL設定
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

