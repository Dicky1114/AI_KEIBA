"""
基底モデルクラス
オブジェクト指向設計の基盤となる共通モデル
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid


class TimeStampedModel(models.Model):
    """
    作成日時・更新日時を自動管理する基底モデル
    """
    created_at = models.DateTimeField(
        verbose_name='作成日時',
        auto_now_add=True,
        help_text='レコードの作成日時'
    )
    updated_at = models.DateTimeField(
        verbose_name='更新日時',
        auto_now=True,
        help_text='レコードの最終更新日時'
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SoftDeleteModel(models.Model):
    """
    論理削除をサポートする基底モデル
    """
    is_deleted = models.BooleanField(
        verbose_name='削除フラグ',
        default=False,
        help_text='論理削除フラグ'
    )
    deleted_at = models.DateTimeField(
        verbose_name='削除日時',
        null=True,
        blank=True,
        help_text='論理削除された日時'
    )
    deleted_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='削除者',
        help_text='削除を実行したユーザー'
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """論理削除を実行"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """論理削除を復元"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class UUIDModel(models.Model):
    """
    UUIDを主キーとして使用する基底モデル
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID',
        help_text='一意識別子'
    )

    class Meta:
        abstract = True


class AuditModel(models.Model):
    """
    作成者・更新者を追跡する基底モデル
    """
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name='作成者',
        help_text='レコードを作成したユーザー'
    )
    updated_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name='更新者',
        help_text='レコードを最後に更新したユーザー'
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """保存時に更新者を自動設定"""
        user = kwargs.pop('user', None)
        if user and not self.pk:
            self.created_by = user
        if user:
            self.updated_by = user
        super().save(*args, **kwargs)


class StatusModel(models.Model):
    """
    ステータス管理を提供する基底モデル
    """
    STATUS_CHOICES = [
        ('active', 'アクティブ'),
        ('inactive', '非アクティブ'),
        ('pending', '保留中'),
        ('processing', '処理中'),
        ('completed', '完了'),
        ('failed', '失敗'),
        ('cancelled', 'キャンセル'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='ステータス',
        help_text='レコードの状態'
    )

    class Meta:
        abstract = True

    def is_active(self):
        """アクティブかどうかを判定"""
        return self.status == 'active'

    def is_pending(self):
        """保留中かどうかを判定"""
        return self.status == 'pending'

    def is_processing(self):
        """処理中かどうかを判定"""
        return self.status == 'processing'

    def is_completed(self):
        """完了かどうかを判定"""
        return self.status == 'completed'

    def is_failed(self):
        """失敗かどうかを判定"""
        return self.status == 'failed'


class VersionModel(models.Model):
    """
    バージョン管理を提供する基底モデル
    """
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='バージョン',
        help_text='レコードのバージョン番号'
    )
    version_comment = models.TextField(
        blank=True,
        verbose_name='バージョンコメント',
        help_text='バージョン更新時のコメント'
    )

    class Meta:
        abstract = True

    def increment_version(self, comment=''):
        """バージョンをインクリメント"""
        self.version += 1
        self.version_comment = comment
        self.save(update_fields=['version', 'version_comment'])


class BaseModel(TimeStampedModel, SoftDeleteModel, AuditModel, StatusModel):
    """
    全ての機能を統合した基底モデル
    """
    class Meta:
        abstract = True

    def __str__(self):
        """文字列表現を定義"""
        if hasattr(self, 'name'):
            return f"{self.name} ({self.get_status_display()})"
        return f"{self.__class__.__name__} #{self.pk}"

    def get_absolute_url(self):
        """詳細ページのURLを取得"""
        return f"/{self._meta.app_label}/{self._meta.model_name}/{self.pk}/"

    def to_dict(self):
        """辞書形式でデータを取得"""
        return {
            'id': self.pk,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status,
            'is_deleted': self.is_deleted,
        }


class CacheModel(models.Model):
    """
    キャッシュ機能を提供する基底モデル
    """
    cache_key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='キャッシュキー',
        help_text='キャッシュの一意キー'
    )
    cache_data = models.JSONField(
        default=dict,
        verbose_name='キャッシュデータ',
        help_text='キャッシュされたデータ'
    )
    cache_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='キャッシュ有効期限',
        help_text='キャッシュの有効期限'
    )

    class Meta:
        abstract = True

    def is_cache_valid(self):
        """キャッシュが有効かどうかを判定"""
        if not self.cache_expires_at:
            return True
        return timezone.now() < self.cache_expires_at

    def invalidate_cache(self):
        """キャッシュを無効化"""
        self.cache_expires_at = timezone.now()
        self.save(update_fields=['cache_expires_at'])


class ConfigurableModel(models.Model):
    """
    設定可能なモデル
    """
    config = models.JSONField(
        default=dict,
        verbose_name='設定',
        help_text='モデルの設定情報'
    )

    class Meta:
        abstract = True

    def get_config(self, key, default=None):
        """設定値を取得"""
        return self.config.get(key, default)

    def set_config(self, key, value):
        """設定値を設定"""
        if not self.config:
            self.config = {}
        self.config[key] = value
        self.save(update_fields=['config'])

    def update_config(self, **kwargs):
        """複数の設定値を一括更新"""
        if not self.config:
            self.config = {}
        self.config.update(kwargs)
        self.save(update_fields=['config'])
