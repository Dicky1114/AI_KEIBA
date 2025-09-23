"""
Accounts API URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'users', api_views.UserViewSet)
router.register(r'preferences', api_views.UserPreferenceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', api_views.LoginAPIView.as_view(), name='api_login'),
    path('auth/logout/', api_views.LogoutAPIView.as_view(), name='api_logout'),
    path('auth/register/', api_views.RegisterAPIView.as_view(), name='api_register'),
]
