"""
基底ビュークラス
オブジェクト指向設計に基づく共通ビュー機能
"""
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
import logging

logger = logging.getLogger(__name__)


class BaseView(View):
    """
    基底ビュークラス
    共通の機能を提供
    """
    
    def dispatch(self, request, *args, **kwargs):
        """リクエスト処理前の共通処理"""
        # ログ出力
        logger.info(f"View accessed: {self.__class__.__name__} by {request.user}")
        
        # リクエスト情報をログに記録
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Request path: {request.path}")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """コンテキストデータを取得"""
        context = super().get_context_data(**kwargs)
        context['current_user'] = self.request.user
        context['is_authenticated'] = self.request.user.is_authenticated
        return context


class BaseTemplateView(BaseView, TemplateView):
    """
    テンプレートビューの基底クラス
    """
    
    def get_template_names(self):
        """テンプレート名を動的に決定"""
        if hasattr(self, 'template_name') and self.template_name:
            return [self.template_name]
        
        # デフォルトのテンプレート名を生成
        app_name = self.__module__.split('.')[1]
        view_name = self.__class__.__name__.lower().replace('view', '')
        return [f"{app_name}/{view_name}.html"]


class BaseListView(BaseView, ListView):
    """
    リストビューの基底クラス
    ページネーションと検索機能を提供
    """
    paginate_by = 20
    search_fields = []
    filter_fields = {}
    ordering = ['-created_at']
    
    def get_queryset(self):
        """クエリセットを取得"""
        queryset = super().get_queryset()
        
        # 検索処理
        search_query = self.request.GET.get('search')
        if search_query and self.search_fields:
            q = Q()
            for field in self.search_fields:
                q |= Q(**{f"{field}__icontains": search_query})
            queryset = queryset.filter(q)
        
        # フィルタ処理
        for field, value in self.request.GET.items():
            if field in self.filter_fields and value:
                filter_kwargs = {self.filter_fields[field]: value}
                queryset = queryset.filter(**filter_kwargs)
        
        return queryset.order_by(*self.ordering)
    
    def get_context_data(self, **kwargs):
        """コンテキストデータを取得"""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['filter_values'] = {
            field: self.request.GET.get(field, '')
            for field in self.filter_fields.keys()
        }
        return context


class BaseDetailView(BaseView, DetailView):
    """
    詳細ビューの基底クラス
    """
    
    def get_object(self, queryset=None):
        """オブジェクトを取得"""
        obj = super().get_object(queryset)
        
        # アクセスログを記録
        logger.info(f"Object accessed: {obj.__class__.__name__} #{obj.pk}")
        
        return obj


class BaseCreateView(BaseView, CreateView):
    """
    作成ビューの基底クラス
    """
    success_message = "作成が完了しました。"
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        logger.info(f"Object created: {self.object.__class__.__name__} #{self.object.pk}")
        return response
    
    def form_invalid(self, form):
        """フォームが無効な場合の処理"""
        messages.error(self.request, "入力内容に誤りがあります。")
        logger.warning(f"Form validation failed: {form.errors}")
        return super().form_invalid(form)


class BaseUpdateView(BaseView, UpdateView):
    """
    更新ビューの基底クラス
    """
    success_message = "更新が完了しました。"
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        logger.info(f"Object updated: {self.object.__class__.__name__} #{self.object.pk}")
        return response
    
    def form_invalid(self, form):
        """フォームが無効な場合の処理"""
        messages.error(self.request, "入力内容に誤りがあります。")
        logger.warning(f"Form validation failed: {form.errors}")
        return super().form_invalid(form)


class BaseDeleteView(BaseView, DeleteView):
    """
    削除ビューの基底クラス
    """
    success_message = "削除が完了しました。"
    
    def delete(self, request, *args, **kwargs):
        """削除処理"""
        self.object = self.get_object()
        logger.info(f"Object deleted: {self.object.__class__.__name__} #{self.object.pk}")
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)


class BaseAPIView(APIView):
    """
    APIビューの基底クラス
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def dispatch(self, request, *args, **kwargs):
        """リクエスト処理前の共通処理"""
        logger.info(f"API accessed: {self.__class__.__name__} by {request.user}")
        return super().dispatch(request, *args, **kwargs)
    
    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK):
        """成功レスポンスを返す"""
        response_data = {
            'success': True,
            'message': message,
        }
        if data is not None:
            response_data['data'] = data
        
        return Response(response_data, status=status_code)
    
    def error_response(self, message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """エラーレスポンスを返す"""
        response_data = {
            'success': False,
            'message': message,
        }
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status_code)


class CachedViewMixin:
    """
    キャッシュ機能を提供するミックスイン
    """
    cache_timeout = 300  # 5分
    
    @method_decorator(cache_page(cache_timeout))
    @method_decorator(vary_on_headers('Authorization'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class AjaxViewMixin:
    """
    AJAXリクエストをサポートするミックスイン
    """
    
    def dispatch(self, request, *args, **kwargs):
        """AJAXリクエストかどうかを判定"""
        self.is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        response = super().form_valid(form)
        
        if self.is_ajax:
            return JsonResponse({
                'success': True,
                'message': getattr(self, 'success_message', 'Success'),
                'redirect_url': self.get_success_url()
            })
        
        return response
    
    def form_invalid(self, form):
        """フォームが無効な場合の処理"""
        if self.is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Validation failed',
                'errors': form.errors
            })
        
        return super().form_invalid(form)


class PermissionMixin(PermissionRequiredMixin):
    """
    権限チェック機能を提供するミックスイン
    """
    permission_denied_message = "この操作を実行する権限がありません。"
    
    def handle_no_permission(self):
        """権限がない場合の処理"""
        messages.error(self.request, self.permission_denied_message)
        return HttpResponseRedirect(self.get_login_url())


class SoftDeleteMixin:
    """
    論理削除機能を提供するミックスイン
    """
    
    def delete(self, request, *args, **kwargs):
        """論理削除を実行"""
        self.object = self.get_object()
        
        if hasattr(self.object, 'soft_delete'):
            self.object.soft_delete(user=request.user)
            messages.success(request, "削除が完了しました。")
        else:
            super().delete(request, *args, **kwargs)
        
        return HttpResponseRedirect(self.get_success_url())


class BulkActionMixin:
    """
    一括操作機能を提供するミックスイン
    """
    bulk_actions = []
    
    def post(self, request, *args, **kwargs):
        """一括操作を処理"""
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_items')
        
        if action in self.bulk_actions and selected_ids:
            queryset = self.get_queryset().filter(id__in=selected_ids)
            
            if action == 'delete':
                if hasattr(queryset.first(), 'soft_delete'):
                    for obj in queryset:
                        obj.soft_delete(user=request.user)
                else:
                    queryset.delete()
                messages.success(request, f"{len(selected_ids)}件のレコードを削除しました。")
            
            elif action == 'activate':
                queryset.update(status='active')
                messages.success(request, f"{len(selected_ids)}件のレコードをアクティブにしました。")
            
            elif action == 'deactivate':
                queryset.update(status='inactive')
                messages.success(request, f"{len(selected_ids)}件のレコードを非アクティブにしました。")
        
        return HttpResponseRedirect(request.path)


class ExportMixin:
    """
    エクスポート機能を提供するミックスイン
    """
    export_formats = ['csv', 'xlsx', 'json']
    
    def get_export_data(self):
        """エクスポート用データを取得"""
        return self.get_queryset()
    
    def export_csv(self, request):
        """CSV形式でエクスポート"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'
        
        writer = csv.writer(response)
        queryset = self.get_export_data()
        
        if queryset.exists():
            # ヘッダー行
            field_names = [field.name for field in queryset.model._meta.fields]
            writer.writerow(field_names)
            
            # データ行
            for obj in queryset:
                row = [getattr(obj, field) for field in field_names]
                writer.writerow(row)
        
        return response
    
    def export_json(self, request):
        """JSON形式でエクスポート"""
        from django.core import serializers
        
        queryset = self.get_export_data()
        data = serializers.serialize('json', queryset)
        
        response = JsonResponse(data, safe=False)
        response['Content-Disposition'] = 'attachment; filename="export.json"'
        return response
