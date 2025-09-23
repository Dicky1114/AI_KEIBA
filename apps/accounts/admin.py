"""
ユーザー管理画面設定
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CustomUser, UserPreference


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    カスタムユーザー管理画面
    """
    list_display = [
        'username', 'email', 'full_name', 'is_premium', 
        'is_staff', 'is_active', 'date_joined', 'profile_image_preview'
    ]
    list_filter = [
        'is_staff', 'is_superuser', 'is_active', 'is_premium', 'date_joined'
    ]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['-date_joined']
    list_per_page = 25
    
    # フィールドセット（編集画面の構成）
    fieldsets = (
        ('基本情報', {
            'fields': ('username', 'email', 'password')
        }),
        ('個人情報', {
            'fields': ('first_name', 'last_name', 'birth_date', 'phone_number', 'bio')
        }),
        ('プロフィール', {
            'fields': ('profile_image',)
        }),
        ('権限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_premium', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('重要な日付', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # 新規作成用フィールドセット
    add_fieldsets = (
        ('必須情報', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
        ('オプション', {
            'classes': ('wide', 'collapse'),
            'fields': ('is_premium', 'is_staff'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login', 'profile_image_preview']
    
    def profile_image_preview(self, obj):
        """プロフィール画像のプレビュー"""
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />',
                obj.profile_image.url
            )
        return "画像なし"
    profile_image_preview.short_description = "プロフィール画像"
    
    def full_name(self, obj):
        """フルネーム表示"""
        return obj.full_name
    full_name.short_description = "氏名"
    
    # アクション
    actions = ['make_premium', 'remove_premium']
    
    def make_premium(self, request, queryset):
        """プレミアム会員にする"""
        updated = queryset.update(is_premium=True)
        self.message_user(request, f'{updated} 人のユーザーをプレミアム会員にしました。')
    make_premium.short_description = "選択されたユーザーをプレミアム会員にする"
    
    def remove_premium(self, request, queryset):
        """プレミアム会員を解除する"""
        updated = queryset.update(is_premium=False)
        self.message_user(request, f'{updated} 人のユーザーのプレミアム会員を解除しました。')
    remove_premium.short_description = "選択されたユーザーのプレミアム会員を解除する"


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """
    ユーザー設定管理画面
    """
    list_display = [
        'user', 'email_notifications', 'race_alerts', 
        'prediction_alerts', 'default_view', 'updated_at'
    ]
    list_filter = [
        'email_notifications', 'race_alerts', 'prediction_alerts', 'default_view'
    ]
    search_fields = ['user__username', 'user__email']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('通知設定', {
            'fields': ('email_notifications', 'race_alerts', 'prediction_alerts')
        }),
        ('表示設定', {
            'fields': ('default_view',)
        }),
        ('分析設定', {
            'fields': ('favorite_tracks',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
