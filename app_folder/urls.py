from .views import login_view, dashboard_view, admin_view
from django.urls import path
from app_folder.admin import admin_site
from django.urls import path
from app_folder import admin_site
from admin import CusAdminSite
from .views.admin_scraping import ScrapingView
from .views.admin_training import TrainingView
# 名前空間の設定
app_name = 'app_folder'

urlpatterns = [
    # 管理画面
    path('admin/', CusAdminSite.urls),
    path("scraping/", admin_view(ScrapingView.as_view()), name="scraping"),
    path("training/", admin_view(TrainingView.as_view()), name="training"),
    # フロント画面
    path('login/', login_view.login_view, name='login'),
	path('dashboard/', dashboard_view.dashboard_view, name='dashboard'), 

    # path('admin/', admin.site.urls),
    # path('admin/', include('app_folder.urls')), 
    # path('run-scraping/', ScrapingView.as_view(), name='run_scraping'),
    # path('register/', register_view.register_view, name='register'),
	# path('data_acquisition/', admin_training.data_acquisition_view, name='data_acquisition'),
]
