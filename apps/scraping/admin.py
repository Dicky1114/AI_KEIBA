from django.contrib import admin
from .models import ScrapingJob, ScrapingSource, ScrapingLog, ScrapingRule, ProxyServer


@admin.register(ScrapingJob)
class ScrapingJobAdmin(admin.ModelAdmin):
    list_display = ['job_type', 'status', 'target_date', 'started_at', 'completed_at']
    list_filter = ['job_type', 'status', 'target_date']
    search_fields = ['target_url']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(ScrapingSource)
class ScrapingSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_url', 'is_active', 'delay_seconds']
    list_filter = ['is_active']
    search_fields = ['name', 'base_url']


@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    list_display = ['job', 'level', 'message', 'url', 'response_code']
    list_filter = ['level', 'response_code']
    search_fields = ['message', 'url']
    date_hierarchy = 'created_at'


@admin.register(ProxyServer)
class ProxyServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'port', 'is_active', 'success_rate']
    list_filter = ['is_active', 'is_working']
    search_fields = ['name', 'host']
