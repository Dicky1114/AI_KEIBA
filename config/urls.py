"""
URL configuration for keiba_prediction project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin URLs
    path('admin/', admin.site.urls),
    
    # App URLs
    path('accounts/', include('apps.accounts.urls')),
    path('races/', include('apps.races.urls')),
    path('horses/', include('apps.horses.urls')),
    path('predictions/', include('apps.predictions.urls')),
    path('scraping/', include('apps.scraping.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('notifications/', include('apps.notifications.urls')),
    
    # API URLs
    path('api/v1/', include('config.api_urls')),
    
    # Frontend URLs
    path('', include('apps.core.urls')),
    
    # Redirect /admin to custom admin dashboard
    path('dashboard/', RedirectView.as_view(url='/admin/', permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Admin site customization
admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE
