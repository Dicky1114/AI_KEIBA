"""
共通モデル
"""
from django.db import models
from django.contrib.auth import get_user_model


class TimeStampedModel(models.Model):
    """
    作成日時・更新日時・作成者・更新者を持つ抽象ベースモデル
    """
    created_at = models.DateTimeField(
        '作成日時', 
        auto_now_add=True,
        help_text='レコードが作成された日時'
    )
    updated_at = models.DateTimeField(
        '更新日時', 
        auto_now=True,
        help_text='レコードが最後に更新された日時'
    )
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name='作成者',
        help_text='このレコードを作成したユーザー'
    )
    updated_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name='更新者',
        help_text='このレコードを最後に更新したユーザー'
    )

    class Meta:
        abstract = True


class RaceClass(models.TextChoices):
    """
    レースクラス選択肢
    """
    NOVICE = 'novice', '新馬'
    MAIDEN = 'maiden', '未勝利'
    ONE_WIN = '1win', '1勝クラス'
    TWO_WIN = '2win', '2勝クラス'
    THREE_WIN = '3win', '3勝クラス'
    LISTED = 'listed', 'リステッド'
    G3 = 'g3', 'G3'
    G2 = 'g2', 'G2'
    G1 = 'g1', 'G1'
    SPECIAL = 'special', '特別レース'


class TrackCondition(models.TextChoices):
    """
    馬場状態選択肢
    """
    FIRM = 'firm', '良'
    GOOD = 'good', '稍重'
    YIELDING = 'yielding', '重'
    SOFT = 'soft', '不良'


class Weather(models.TextChoices):
    """
    天候選択肢
    """
    FINE = 'fine', '晴'
    CLOUDY = 'cloudy', '曇'
    RAINY = 'rainy', '雨'
    SNOWY = 'snowy', '雪'
