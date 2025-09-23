"""
API URL configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('accounts/', include('apps.accounts.api_urls')),
    path('races/', include('apps.races.api_urls')),
    path('horses/', include('apps.horses.api_urls')),
    path('predictions/', include('apps.predictions.api_urls')),
    path('scraping/', include('apps.scraping.api_urls')),
    path('analytics/', include('apps.analytics.api_urls')),
    path('notifications/', include('apps.notifications.api_urls')),
]
