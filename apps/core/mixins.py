"""
共通Mixinクラス
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import JsonResponse


class TimestampMixin(models.Model):
    """
    タイムスタンプ機能を提供するMixin
    """
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True


class UserTrackingMixin(models.Model):
    """
    ユーザー追跡機能を提供するMixin
    """
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name='作成者'
    )
    updated_by = models.ForeignKey(
        'accounts.CustomUser', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name='更新者'
    )

    class Meta:
        abstract = True


class APIResponseMixin:
    """
    API レスポンス用のMixin
    """
    def json_response(self, data, status=200):
        """
        JSON レスポンスを返す
        """
        return JsonResponse(data, status=status, safe=False)

    def success_response(self, data=None, message='Success'):
        """
        成功レスポンス
        """
        response_data = {
            'status': 'success',
            'message': message,
        }
        if data is not None:
            response_data['data'] = data
        return self.json_response(response_data)

    def error_response(self, message='Error', errors=None, status=400):
        """
        エラーレスポンス
        """
        response_data = {
            'status': 'error',
            'message': message,
        }
        if errors:
            response_data['errors'] = errors
        return self.json_response(response_data, status=status)


class AdminOnlyMixin(LoginRequiredMixin):
    """
    管理者のみアクセス可能なMixin
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("管理者権限が必要です。")
        return super().dispatch(request, *args, **kwargs)


class StaffOnlyMixin(LoginRequiredMixin):
    """
    スタッフのみアクセス可能なMixin
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("スタッフ権限が必要です。")
        return super().dispatch(request, *args, **kwargs)


class AjaxResponseMixin:
    """
    AJAX リクエスト対応Mixin
    """
    def dispatch(self, request, *args, **kwargs):
        self.is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.is_ajax:
            return self.success_response(data={'redirect_url': self.get_success_url()})
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.is_ajax:
            return self.error_response(
                message='フォームにエラーがあります。',
                errors=form.errors
            )
        return response
