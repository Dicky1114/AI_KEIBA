from django.contrib import admin
from .models import Venue, Race, RaceEntry, RaceResult


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'location', 'created_at']
    list_filter = ['location']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'venue', 'race_date', 'race_number', 'distance', 'is_grade_race']
    list_filter = ['venue', 'race_date', 'race_class', 'track_type', 'is_grade_race']
    search_fields = ['name', 'race_id']
    date_hierarchy = 'race_date'
    ordering = ['-race_date', 'race_number']


@admin.register(RaceEntry)
class RaceEntryAdmin(admin.ModelAdmin):
    list_display = ['race', 'horse_number', 'horse', 'jockey', 'weight', 'popularity']
    list_filter = ['race__venue', 'race__race_date']
    search_fields = ['horse__name', 'jockey__name', 'race__name']
    ordering = ['race__race_date', 'horse_number']


@admin.register(RaceResult)
class RaceResultAdmin(admin.ModelAdmin):
    list_display = ['entry', 'finish_position', 'finish_time', 'win_payout']
    list_filter = ['entry__race__venue', 'entry__race__race_date', 'finish_position']
    search_fields = ['entry__horse__name', 'entry__race__name']
    ordering = ['entry__race__race_date', 'finish_position']
