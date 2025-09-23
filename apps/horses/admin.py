from django.contrib import admin
from .models import Horse, Jockey, HorsePerformance


@admin.register(Horse)
class HorseAdmin(admin.ModelAdmin):
    list_display = ['name', 'birth_date', 'sex', 'owner', 'trainer']
    list_filter = ['sex', 'birth_date']
    search_fields = ['name', 'owner', 'trainer']
    date_hierarchy = 'birth_date'
    ordering = ['name']


@admin.register(Jockey)
class JockeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'stable', 'license_type', 'win_rate', 'total_races']
    list_filter = ['license_type', 'stable']
    search_fields = ['name', 'stable']
    ordering = ['name']


@admin.register(HorsePerformance)
class HorsePerformanceAdmin(admin.ModelAdmin):
    list_display = ['horse', 'race', 'finish_position', 'jockey', 'finish_time']
    list_filter = ['race__venue', 'race__race_date', 'finish_position']
    search_fields = ['horse__name', 'jockey__name', 'race__name']
    ordering = ['-race__race_date']
