# accounts/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    # ログアウトURLの設定
	path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
