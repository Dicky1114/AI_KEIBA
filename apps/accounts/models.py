"""
ユーザー関連モデル
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    カスタムユーザーモデル
    """
    email = models.EmailField('メールアドレス', unique=True)
    first_name = models.CharField('名', max_length=30)
    last_name = models.CharField('姓', max_length=30)
    is_premium = models.BooleanField('プレミアム会員', default=False)
    date_joined = models.DateTimeField('登録日時', auto_now_add=True)
    last_login = models.DateTimeField('最終ログイン', null=True, blank=True)
    
    # 追加フィールド
    profile_image = models.ImageField(
        'プロフィール画像',
        upload_to='profiles/',
        null=True,
        blank=True
    )
    bio = models.TextField('自己紹介', max_length=500, blank=True)
    birth_date = models.DateField('生年月日', null=True, blank=True)
    phone_number = models.CharField('電話番号', max_length=15, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
        
    def __str__(self):
        return f'{self.last_name} {self.first_name} ({self.username})'
    
    @property
    def full_name(self):
        return f'{self.last_name} {self.first_name}'
    
    def get_display_name(self):
        """表示用の名前を取得"""
        if self.first_name and self.last_name:
            return self.full_name
        return self.username


class UserPreference(models.Model):
    """
    ユーザー設定
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='preferences',
        verbose_name='ユーザー'
    )
    
    # 通知設定
    email_notifications = models.BooleanField('メール通知', default=True)
    race_alerts = models.BooleanField('レース結果通知', default=True)
    prediction_alerts = models.BooleanField('予測結果通知', default=False)
    
    # 表示設定
    default_view = models.CharField(
        'デフォルト表示',
        max_length=20,
        choices=[
            ('dashboard', 'ダッシュボード'),
            ('races', 'レース一覧'),
            ('predictions', '予測一覧'),
        ],
        default='dashboard'
    )
    
    # 分析設定
    favorite_tracks = models.JSONField('お気に入り競馬場', default=list, blank=True)
    
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'ユーザー設定'
        verbose_name_plural = 'ユーザー設定'
        
    def __str__(self):
        return f'{self.user.username}の設定'
