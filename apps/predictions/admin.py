from django.contrib import admin
from .models import Prediction, PredictionModel


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ['race', 'predicted_winner', 'confidence_score', 'model_version', 'is_correct']
    list_filter = ['model_version', 'is_correct', 'race__race_date']
    search_fields = ['race__name', 'predicted_winner__horse__name']
    date_hierarchy = 'race__race_date'
    ordering = ['-race__race_date']


@admin.register(PredictionModel)
class PredictionModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'algorithm', 'accuracy', 'is_active']
    list_filter = ['algorithm', 'is_active']
    search_fields = ['name', 'version']
    ordering = ['-created_at']
