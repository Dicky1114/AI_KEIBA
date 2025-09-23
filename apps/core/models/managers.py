"""
カスタムマネージャークラス
オブジェクト指向設計に基づくクエリセット管理
"""
from django.db import models
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.utils import timezone
from datetime import datetime, timedelta


class BaseManager(models.Manager):
    """
    基底マネージャークラス
    共通のクエリメソッドを提供
    """
    
    def active(self):
        """アクティブなレコードを取得"""
        return self.filter(status='active')
    
    def inactive(self):
        """非アクティブなレコードを取得"""
        return self.filter(status='inactive')
    
    def recent(self, days=30):
        """最近のレコードを取得"""
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)
    
    def by_user(self, user):
        """特定のユーザーに関連するレコードを取得"""
        return self.filter(
            Q(created_by=user) | Q(updated_by=user)
        )


class SoftDeleteManager(BaseManager):
    """
    論理削除をサポートするマネージャー
    """
    
    def get_queryset(self):
        """論理削除されていないレコードのみを取得"""
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """論理削除されたレコードも含めて取得"""
        return super().get_queryset()
    
    def only_deleted(self):
        """論理削除されたレコードのみを取得"""
        return super().get_queryset().filter(is_deleted=True)
    
    def restore(self, *args, **kwargs):
        """論理削除されたレコードを復元"""
        return self.only_deleted().update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None
        )


class StatusManager(BaseManager):
    """
    ステータス管理をサポートするマネージャー
    """
    
    def pending(self):
        """保留中のレコードを取得"""
        return self.filter(status='pending')
    
    def processing(self):
        """処理中のレコードを取得"""
        return self.filter(status='processing')
    
    def completed(self):
        """完了したレコードを取得"""
        return self.filter(status='completed')
    
    def failed(self):
        """失敗したレコードを取得"""
        return self.filter(status='failed')
    
    def cancelled(self):
        """キャンセルされたレコードを取得"""
        return self.filter(status='cancelled')


class TimeRangeManager(BaseManager):
    """
    時間範囲でのクエリをサポートするマネージャー
    """
    
    def today(self):
        """今日のレコードを取得"""
        today = timezone.now().date()
        return self.filter(created_at__date=today)
    
    def this_week(self):
        """今週のレコードを取得"""
        now = timezone.now()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return self.filter(
            created_at__date__range=[start_of_week.date(), end_of_week.date()]
        )
    
    def this_month(self):
        """今月のレコードを取得"""
        now = timezone.now()
        return self.filter(
            created_at__year=now.year,
            created_at__month=now.month
        )
    
    def this_year(self):
        """今年のレコードを取得"""
        now = timezone.now()
        return self.filter(created_at__year=now.year)
    
    def between_dates(self, start_date, end_date):
        """指定期間のレコードを取得"""
        return self.filter(
            created_at__date__range=[start_date, end_date]
        )


class SearchManager(BaseManager):
    """
    検索機能をサポートするマネージャー
    """
    
    def search(self, query, fields=None):
        """テキスト検索を実行"""
        if not query:
            return self.none()
        
        if fields is None:
            fields = ['name', 'description']
        
        q = Q()
        for field in fields:
            q |= Q(**{f"{field}__icontains": query})
        
        return self.filter(q)
    
    def filter_by_keywords(self, keywords, fields=None):
        """キーワードでフィルタリング"""
        if not keywords:
            return self.none()
        
        if isinstance(keywords, str):
            keywords = keywords.split()
        
        if fields is None:
            fields = ['name', 'description']
        
        q = Q()
        for keyword in keywords:
            for field in fields:
                q |= Q(**{f"{field}__icontains": keyword})
        
        return self.filter(q)


class AnalyticsManager(BaseManager):
    """
    分析機能をサポートするマネージャー
    """
    
    def get_statistics(self):
        """基本統計を取得"""
        return self.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status='active')),
            inactive=Count('id', filter=Q(status='inactive')),
        )
    
    def get_growth_rate(self, days=30):
        """成長率を計算"""
        now = timezone.now()
        current_period = self.filter(
            created_at__gte=now - timedelta(days=days)
        ).count()
        
        previous_period = self.filter(
            created_at__gte=now - timedelta(days=days*2),
            created_at__lt=now - timedelta(days=days)
        ).count()
        
        if previous_period == 0:
            return 0
        
        return ((current_period - previous_period) / previous_period) * 100
    
    def get_top_items(self, field, limit=10):
        """上位アイテムを取得"""
        return self.values(field).annotate(
            count=Count('id')
        ).order_by('-count')[:limit]


class CacheManager(BaseManager):
    """
    キャッシュ機能をサポートするマネージャー
    """
    
    def get_cached(self, cache_key):
        """キャッシュされたデータを取得"""
        try:
            obj = self.get(cache_key=cache_key)
            if obj.is_cache_valid():
                return obj.cache_data
            else:
                obj.invalidate_cache()
                return None
        except self.model.DoesNotExist:
            return None
    
    def set_cache(self, cache_key, data, expires_in_hours=24):
        """データをキャッシュに保存"""
        expires_at = timezone.now() + timedelta(hours=expires_in_hours)
        
        obj, created = self.get_or_create(
            cache_key=cache_key,
            defaults={
                'cache_data': data,
                'cache_expires_at': expires_at
            }
        )
        
        if not created:
            obj.cache_data = data
            obj.cache_expires_at = expires_at
            obj.save(update_fields=['cache_data', 'cache_expires_at'])
        
        return obj


class CompositeManager(SoftDeleteManager, StatusManager, TimeRangeManager, SearchManager, AnalyticsManager):
    """
    複数のマネージャーを組み合わせた統合マネージャー
    """
    pass


class PredictionManager(CompositeManager):
    """
    予測モデル専用のマネージャー
    """
    
    def by_race(self, race):
        """特定のレースの予測を取得"""
        return self.filter(race=race)
    
    def by_model(self, model):
        """特定のモデルの予測を取得"""
        return self.filter(model=model)
    
    def successful_predictions(self):
        """成功した予測を取得"""
        return self.filter(is_correct=True)
    
    def failed_predictions(self):
        """失敗した予測を取得"""
        return self.filter(is_correct=False)
    
    def get_accuracy_rate(self, model=None):
        """精度率を計算"""
        queryset = self
        if model:
            queryset = queryset.filter(model=model)
        
        total = queryset.count()
        if total == 0:
            return 0
        
        correct = queryset.filter(is_correct=True).count()
        return (correct / total) * 100
    
    def get_confidence_stats(self):
        """信頼度の統計を取得"""
        return self.aggregate(
            avg_confidence=Avg('confidence_score'),
            max_confidence=Max('confidence_score'),
            min_confidence=Min('confidence_score'),
        )


class RaceManager(CompositeManager):
    """
    レースモデル専用のマネージャー
    """
    
    def upcoming(self):
        """今後のレースを取得"""
        return self.filter(race_date__gte=timezone.now().date())
    
    def past(self):
        """過去のレースを取得"""
        return self.filter(race_date__lt=timezone.now().date())
    
    def by_venue(self, venue):
        """特定の競馬場のレースを取得"""
        return self.filter(venue=venue)
    
    def grade_races(self):
        """重賞レースを取得"""
        return self.filter(is_grade_race=True)
    
    def by_distance_range(self, min_distance, max_distance):
        """距離範囲でフィルタリング"""
        return self.filter(
            distance__gte=min_distance,
            distance__lte=max_distance
        )


class HorseManager(CompositeManager):
    """
    馬モデル専用のマネージャー
    """
    
    def by_sex(self, sex):
        """性別でフィルタリング"""
        return self.filter(sex=sex)
    
    def by_age(self, age):
        """年齢でフィルタリング"""
        return self.filter(age=age)
    
    def active_horses(self):
        """現役馬を取得"""
        return self.filter(status='active')
    
    def retired_horses(self):
        """引退馬を取得"""
        return self.filter(status='retired')
    
    def get_performance_stats(self):
        """成績統計を取得"""
        return self.aggregate(
            total_races=Sum('total_races'),
            wins=Sum('wins'),
            places=Sum('places'),
            shows=Sum('shows'),
        )
