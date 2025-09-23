"""
基底サービスクラス
ビジネスロジックを分離し、再利用可能なサービス層を提供
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseService(ABC):
    """
    基底サービスクラス
    全てのサービスクラスの共通インターフェース
    """
    
    def __init__(self, model: Type[models.Model]):
        self.model = model
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @abstractmethod
    def create(self, **kwargs) -> models.Model:
        """オブジェクトを作成"""
        pass
    
    @abstractmethod
    def get(self, **kwargs) -> Optional[models.Model]:
        """オブジェクトを取得"""
        pass
    
    @abstractmethod
    def update(self, obj: models.Model, **kwargs) -> models.Model:
        """オブジェクトを更新"""
        pass
    
    @abstractmethod
    def delete(self, obj: models.Model) -> bool:
        """オブジェクトを削除"""
        pass
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """データを検証"""
        return data
    
    def log_operation(self, operation: str, obj: models.Model, user: Optional[User] = None):
        """操作をログに記録"""
        self.logger.info(
            f"{operation}: {self.model.__name__} #{obj.pk} by {user or 'System'}"
        )


class CRUDService(BaseService):
    """
    CRUD操作を提供するサービスクラス
    """
    
    def create(self, user: Optional[User] = None, **kwargs) -> models.Model:
        """オブジェクトを作成"""
        try:
            # データ検証
            validated_data = self.validate_data(kwargs)
            
            # ユーザー情報を追加
            if user and hasattr(self.model, 'created_by'):
                validated_data['created_by'] = user
            if user and hasattr(self.model, 'updated_by'):
                validated_data['updated_by'] = user
            
            with transaction.atomic():
                obj = self.model.objects.create(**validated_data)
                self.log_operation("CREATE", obj, user)
                return obj
                
        except Exception as e:
            self.logger.error(f"Create failed: {e}")
            raise
    
    def get(self, **kwargs) -> Optional[models.Model]:
        """オブジェクトを取得"""
        try:
            return self.model.objects.get(**kwargs)
        except self.model.DoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"Get failed: {e}")
            raise
    
    def get_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> tuple[models.Model, bool]:
        """オブジェクトを取得または作成"""
        try:
            defaults = defaults or {}
            return self.model.objects.get_or_create(defaults=defaults, **kwargs)
        except Exception as e:
            self.logger.error(f"Get or create failed: {e}")
            raise
    
    def update(self, obj: models.Model, user: Optional[User] = None, **kwargs) -> models.Model:
        """オブジェクトを更新"""
        try:
            # データ検証
            validated_data = self.validate_data(kwargs)
            
            # ユーザー情報を追加
            if user and hasattr(obj, 'updated_by'):
                validated_data['updated_by'] = user
            
            with transaction.atomic():
                for key, value in validated_data.items():
                    setattr(obj, key, value)
                obj.save()
                self.log_operation("UPDATE", obj, user)
                return obj
                
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            raise
    
    def delete(self, obj: models.Model, user: Optional[User] = None) -> bool:
        """オブジェクトを削除"""
        try:
            with transaction.atomic():
                if hasattr(obj, 'soft_delete'):
                    obj.soft_delete(user=user)
                else:
                    obj.delete()
                self.log_operation("DELETE", obj, user)
                return True
                
        except Exception as e:
            self.logger.error(f"Delete failed: {e}")
            raise
    
    def bulk_create(self, data_list: List[Dict], user: Optional[User] = None) -> List[models.Model]:
        """一括作成"""
        try:
            objects = []
            for data in data_list:
                validated_data = self.validate_data(data)
                if user and hasattr(self.model, 'created_by'):
                    validated_data['created_by'] = user
                if user and hasattr(self.model, 'updated_by'):
                    validated_data['updated_by'] = user
                
                obj = self.model(**validated_data)
                objects.append(obj)
            
            with transaction.atomic():
                created_objects = self.model.objects.bulk_create(objects)
                for obj in created_objects:
                    self.log_operation("BULK_CREATE", obj, user)
                return created_objects
                
        except Exception as e:
            self.logger.error(f"Bulk create failed: {e}")
            raise
    
    def bulk_update(self, objects: List[models.Model], fields: List[str], user: Optional[User] = None) -> List[models.Model]:
        """一括更新"""
        try:
            if user and 'updated_by' in fields and hasattr(objects[0], 'updated_by'):
                for obj in objects:
                    obj.updated_by = user
            
            with transaction.atomic():
                self.model.objects.bulk_update(objects, fields)
                for obj in objects:
                    self.log_operation("BULK_UPDATE", obj, user)
                return objects
                
        except Exception as e:
            self.logger.error(f"Bulk update failed: {e}")
            raise


class QueryService(BaseService):
    """
    クエリ操作を提供するサービスクラス
    """
    
    def filter(self, **kwargs) -> models.QuerySet:
        """フィルタリング"""
        return self.model.objects.filter(**kwargs)
    
    def exclude(self, **kwargs) -> models.QuerySet:
        """除外"""
        return self.model.objects.exclude(**kwargs)
    
    def all(self) -> models.QuerySet:
        """全件取得"""
        return self.model.objects.all()
    
    def count(self, **kwargs) -> int:
        """件数取得"""
        return self.model.objects.filter(**kwargs).count()
    
    def exists(self, **kwargs) -> bool:
        """存在確認"""
        return self.model.objects.filter(**kwargs).exists()
    
    def first(self, **kwargs) -> Optional[models.Model]:
        """最初のオブジェクトを取得"""
        return self.model.objects.filter(**kwargs).first()
    
    def last(self, **kwargs) -> Optional[models.Model]:
        """最後のオブジェクトを取得"""
        return self.model.objects.filter(**kwargs).last()


class SearchService(BaseService):
    """
    検索機能を提供するサービスクラス
    """
    
    def __init__(self, model: Type[models.Model], search_fields: List[str]):
        super().__init__(model)
        self.search_fields = search_fields
    
    def search(self, query: str) -> models.QuerySet:
        """テキスト検索"""
        if not query:
            return self.model.objects.none()
        
        from django.db.models import Q
        
        q = Q()
        for field in self.search_fields:
            q |= Q(**{f"{field}__icontains": query})
        
        return self.model.objects.filter(q)
    
    def advanced_search(self, filters: Dict[str, Any]) -> models.QuerySet:
        """高度な検索"""
        queryset = self.model.objects.all()
        
        for field, value in filters.items():
            if value is not None and value != '':
                if field.endswith('__gte'):
                    queryset = queryset.filter(**{field: value})
                elif field.endswith('__lte'):
                    queryset = queryset.filter(**{field: value})
                elif field.endswith('__icontains'):
                    queryset = queryset.filter(**{field: value})
                else:
                    queryset = queryset.filter(**{field: value})
        
        return queryset


class CacheService(BaseService):
    """
    キャッシュ機能を提供するサービスクラス
    """
    
    def __init__(self, model: Type[models.Model], cache_timeout: int = 300):
        super().__init__(model)
        self.cache_timeout = cache_timeout
    
    def get_cached(self, cache_key: str) -> Optional[Any]:
        """キャッシュから取得"""
        from django.core.cache import cache
        return cache.get(cache_key)
    
    def set_cache(self, cache_key: str, data: Any) -> None:
        """キャッシュに保存"""
        from django.core.cache import cache
        cache.set(cache_key, data, self.cache_timeout)
    
    def delete_cache(self, cache_key: str) -> None:
        """キャッシュを削除"""
        from django.core.cache import cache
        cache.delete(cache_key)
    
    def get_or_set_cache(self, cache_key: str, callable_func, *args, **kwargs) -> Any:
        """キャッシュから取得、なければ実行してキャッシュに保存"""
        from django.core.cache import cache
        return cache.get_or_set(cache_key, callable_func, self.cache_timeout, *args, **kwargs)


class ValidationService(BaseService):
    """
    バリデーション機能を提供するサービスクラス
    """
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """必須フィールドの検証"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationError(f"必須フィールドが不足しています: {', '.join(missing_fields)}")
    
    def validate_field_types(self, data: Dict[str, Any], field_types: Dict[str, Type]) -> None:
        """フィールドタイプの検証"""
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    raise ValidationError(f"{field}は{expected_type.__name__}型である必要があります")
    
    def validate_unique_fields(self, data: Dict[str, Any], unique_fields: List[str], exclude_id: Optional[int] = None) -> None:
        """ユニークフィールドの検証"""
        for field in unique_fields:
            if field in data and data[field] is not None:
                queryset = self.model.objects.filter(**{field: data[field]})
                if exclude_id:
                    queryset = queryset.exclude(id=exclude_id)
                if queryset.exists():
                    raise ValidationError(f"{field}は既に存在します")


class NotificationService(BaseService):
    """
    通知機能を提供するサービスクラス
    """
    
    def send_notification(self, user: User, message: str, notification_type: str = 'info') -> None:
        """通知を送信"""
        try:
            # 通知モデルが存在する場合
            if hasattr(self.model, 'create_notification'):
                self.model.create_notification(
                    user=user,
                    message=message,
                    notification_type=notification_type
                )
            
            # ログに記録
            self.logger.info(f"Notification sent to {user}: {message}")
            
        except Exception as e:
            self.logger.error(f"Notification failed: {e}")


class ExportService(BaseService):
    """
    エクスポート機能を提供するサービスクラス
    """
    
    def export_to_csv(self, queryset: models.QuerySet, filename: str) -> str:
        """CSV形式でエクスポート"""
        import csv
        import os
        from django.conf import settings
        
        filepath = os.path.join(settings.MEDIA_ROOT, 'exports', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            if queryset.exists():
                field_names = [field.name for field in queryset.model._meta.fields]
                writer = csv.DictWriter(csvfile, fieldnames=field_names)
                writer.writeheader()
                
                for obj in queryset:
                    row = {field: getattr(obj, field) for field in field_names}
                    writer.writerow(row)
        
        return filepath
    
    def export_to_json(self, queryset: models.QuerySet, filename: str) -> str:
        """JSON形式でエクスポート"""
        import json
        import os
        from django.conf import settings
        from django.core import serializers
        
        filepath = os.path.join(settings.MEDIA_ROOT, 'exports', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = serializers.serialize('json', queryset)
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, ensure_ascii=False, indent=2)
        
        return filepath
