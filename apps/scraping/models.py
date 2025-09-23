"""
スクレイピング関連モデル
"""
from django.db import models
from apps.core.models import TimeStampedModel


class ScrapingJob(TimeStampedModel):
    """
    スクレイピングジョブ管理
    """
    JOB_TYPE_CHOICES = [
        ('race_data', 'レースデータ'),
        ('horse_data', '馬データ'),
        ('jockey_data', '騎手データ'),
        ('odds_data', 'オッズデータ'),
        ('result_data', '結果データ'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待機中'),
        ('running', '実行中'),
        ('completed', '完了'),
        ('failed', '失敗'),
        ('cancelled', 'キャンセル'),
    ]
    
    job_type = models.CharField('ジョブタイプ', max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='pending')
    target_url = models.URLField('対象URL', blank=True)
    target_date = models.DateField('対象日', null=True, blank=True)
    
    # ジョブ詳細情報
    parameters = models.JSONField('パラメータ', default=dict, blank=True)
    result_data = models.JSONField('結果データ', default=dict, blank=True)
    error_message = models.TextField('エラーメッセージ', blank=True)
    
    # 実行情報
    started_at = models.DateTimeField('開始時刻', null=True, blank=True)
    completed_at = models.DateTimeField('完了時刻', null=True, blank=True)
    retry_count = models.IntegerField('リトライ回数', default=0)
    
    class Meta:
        verbose_name = 'スクレイピングジョブ'
        verbose_name_plural = 'スクレイピングジョブ'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_job_type_display()} - {self.get_status_display()}"


class ScrapingSource(TimeStampedModel):
    """
    スクレイピング対象サイト管理
    """
    name = models.CharField('サイト名', max_length=100)
    base_url = models.URLField('ベースURL')
    is_active = models.BooleanField('アクティブ', default=True)
    
    # アクセス設定
    delay_seconds = models.FloatField('アクセス間隔（秒）', default=1.0)
    max_retries = models.IntegerField('最大リトライ回数', default=3)
    timeout_seconds = models.IntegerField('タイムアウト（秒）', default=30)
    
    # HTTP設定
    user_agent = models.TextField('User-Agent', blank=True)
    headers = models.JSONField('HTTPヘッダー', default=dict, blank=True)
    cookies = models.JSONField('Cookie', default=dict, blank=True)
    
    # レート制限
    requests_per_minute = models.IntegerField('分間リクエスト数制限', default=60)
    daily_request_limit = models.IntegerField('日間リクエスト数制限', default=10000)
    
    class Meta:
        verbose_name = 'スクレイピング対象サイト'
        verbose_name_plural = 'スクレイピング対象サイト'
    
    def __str__(self):
        return self.name


class ScrapingLog(TimeStampedModel):
    """
    スクレイピング実行ログ
    """
    LOG_LEVEL_CHOICES = [
        ('debug', 'DEBUG'),
        ('info', 'INFO'),
        ('warning', 'WARNING'),
        ('error', 'ERROR'),
        ('critical', 'CRITICAL'),
    ]
    
    job = models.ForeignKey(ScrapingJob, on_delete=models.CASCADE, related_name='logs')
    level = models.CharField('ログレベル', max_length=10, choices=LOG_LEVEL_CHOICES)
    message = models.TextField('メッセージ')
    url = models.URLField('URL', blank=True)
    
    # 技術的詳細
    response_code = models.IntegerField('レスポンスコード', null=True, blank=True)
    response_time = models.FloatField('レスポンス時間（秒）', null=True, blank=True)
    data_size = models.IntegerField('データサイズ（バイト）', null=True, blank=True)
    
    class Meta:
        verbose_name = 'スクレイピングログ'
        verbose_name_plural = 'スクレイピングログ'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.job} - {self.level.upper()}: {self.message[:50]}"


class ScrapingRule(TimeStampedModel):
    """
    スクレイピングルール設定
    """
    RULE_TYPE_CHOICES = [
        ('css_selector', 'CSSセレクター'),
        ('xpath', 'XPath'),
        ('regex', '正規表現'),
        ('json_path', 'JSONPath'),
    ]
    
    name = models.CharField('ルール名', max_length=100)
    source = models.ForeignKey(ScrapingSource, on_delete=models.CASCADE, related_name='rules')
    rule_type = models.CharField('ルール種別', max_length=20, choices=RULE_TYPE_CHOICES)
    
    # セレクター設定
    selector = models.TextField('セレクター')
    attribute = models.CharField('属性名', max_length=50, blank=True)
    
    # データ処理設定
    field_name = models.CharField('フィールド名', max_length=50)
    data_type = models.CharField('データ型', max_length=20, choices=[
        ('text', 'テキスト'),
        ('number', '数値'),
        ('date', '日付'),
        ('url', 'URL'),
        ('boolean', '真偽値'),
    ], default='text')
    
    # 前処理設定
    preprocessing_rules = models.JSONField('前処理ルール', default=list, blank=True)
    validation_rules = models.JSONField('バリデーションルール', default=list, blank=True)
    
    is_required = models.BooleanField('必須項目', default=False)
    is_active = models.BooleanField('アクティブ', default=True)
    
    class Meta:
        verbose_name = 'スクレイピングルール'
        verbose_name_plural = 'スクレイピングルール'
        unique_together = ['source', 'field_name']
    
    def __str__(self):
        return f"{self.source.name} - {self.name}"


class RateLimitLog(TimeStampedModel):
    """
    レート制限ログ
    """
    source = models.ForeignKey(ScrapingSource, on_delete=models.CASCADE, related_name='rate_logs')
    requests_count = models.IntegerField('リクエスト数')
    time_window = models.DurationField('時間窓')
    is_limit_exceeded = models.BooleanField('制限超過', default=False)
    
    class Meta:
        verbose_name = 'レート制限ログ'
        verbose_name_plural = 'レート制限ログ'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.source.name} - {self.requests_count} requests"


class ProxyServer(TimeStampedModel):
    """
    プロキシサーバー管理
    """
    name = models.CharField('プロキシ名', max_length=100)
    host = models.CharField('ホスト', max_length=255)
    port = models.IntegerField('ポート')
    username = models.CharField('ユーザー名', max_length=100, blank=True)
    password = models.CharField('パスワード', max_length=100, blank=True)
    
    is_active = models.BooleanField('アクティブ', default=True)
    is_working = models.BooleanField('動作中', default=True)
    
    # 統計情報
    success_count = models.IntegerField('成功回数', default=0)
    failure_count = models.IntegerField('失敗回数', default=0)
    last_used_at = models.DateTimeField('最終使用時刻', null=True, blank=True)
    last_check_at = models.DateTimeField('最終チェック時刻', null=True, blank=True)
    
    class Meta:
        verbose_name = 'プロキシサーバー'
        verbose_name_plural = 'プロキシサーバー'
        unique_together = ['host', 'port']
    
    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"
    
    @property
    def success_rate(self):
        """成功率を計算"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0
        return (self.success_count / total) * 100