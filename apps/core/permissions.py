"""
カスタム権限クラス
"""
from rest_framework import permissions
from django.contrib.auth.models import AnonymousUser


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    作成者のみ編集可能、他は読み取り専用
    """
    def has_object_permission(self, request, view, obj):
        # 読み取り権限は全員に許可
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 書き込み権限は作成者のみ
        return obj.created_by == request.user


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    スタッフのみ編集可能、他は読み取り専用
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    管理者のみ編集可能、他は読み取り専用
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser


class IsPredictionOwner(permissions.BasePermission):
    """
    予測の作成者のみアクセス可能
    """
    def has_object_permission(self, request, view, obj):
        # 予測は作成者のみアクセス可能
        return obj.created_by == request.user


class IsAnalyticsUser(permissions.BasePermission):
    """
    分析機能へのアクセス権限
    """
    def has_permission(self, request, view):
        # 認証済みユーザーで、分析権限を持つユーザーのみ
        if isinstance(request.user, AnonymousUser):
            return False
        
        # カスタムユーザーに analytics_access フィールドがある場合
        return getattr(request.user, 'can_access_analytics', False) or request.user.is_staff


class IsScrapingUser(permissions.BasePermission):
    """
    スクレイピング機能へのアクセス権限
    """
    def has_permission(self, request, view):
        # スタッフまたは管理者のみ
        return request.user.is_staff or request.user.is_superuser


class IsModelManager(permissions.BasePermission):
    """
    機械学習モデル管理権限
    """
    def has_permission(self, request, view):
        # 管理者またはモデル管理者のみ
        if request.user.is_superuser:
            return True
        
        # カスタムユーザーに model_manager フィールドがある場合
        return getattr(request.user, 'is_model_manager', False)


class CanViewPredictions(permissions.BasePermission):
    """
    予測結果閲覧権限
    """
    def has_permission(self, request, view):
        # 認証済みユーザーで、有料プランまたはスタッフ
        if isinstance(request.user, AnonymousUser):
            return False
        
        # 無料ユーザーは制限された予測のみ閲覧可能
        return request.user.is_authenticated


class CanAccessPremiumFeatures(permissions.BasePermission):
    """
    プレミアム機能アクセス権限
    """
    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False
        
        # プレミアムユーザーまたはスタッフ
        return (getattr(request.user, 'is_premium', False) or 
                request.user.is_staff or 
                request.user.is_superuser)


class RaceDataPermission(permissions.BasePermission):
    """
    レースデータに対する権限
    """
    def has_permission(self, request, view):
        # GET は全員許可
        if request.method == 'GET':
            return True
        
        # POST, PUT, DELETE はスタッフのみ
        return request.user.is_staff

    def has_object_permission(self, request, view, obj):
        # 読み取りは全員許可
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 編集はスタッフのみ
        return request.user.is_staff


class HorseDataPermission(permissions.BasePermission):
    """
    馬データに対する権限
    """
    def has_permission(self, request, view):
        # 基本的にはスタッフのみデータ操作可能
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff


class NotificationPermission(permissions.BasePermission):
    """
    通知に対する権限
    """
    def has_object_permission(self, request, view, obj):
        # 自分の通知のみアクセス可能
        return obj.user == request.user
