"""
予測関連モデル
"""
from django.db import models
from apps.core.models import TimeStampedModel


class Prediction(TimeStampedModel):
    """
    予測結果モデル
    """
    race = models.ForeignKey('races.Race', on_delete=models.CASCADE, related_name='predictions')
    
    # 予測情報
    predicted_winner = models.ForeignKey('races.RaceEntry', on_delete=models.CASCADE, 
                                       related_name='winner_predictions')
    confidence_score = models.FloatField('信頼度スコア', help_text='0.0-1.0の範囲')
    
    # AI予測詳細
    model_version = models.CharField('モデルバージョン', max_length=50)
    prediction_data = models.JSONField('予測データ', default=dict)
    
    # 結果検証
    is_correct = models.BooleanField('予測的中', null=True, blank=True)
    actual_result = models.ForeignKey('races.RaceResult', on_delete=models.SET_NULL, 
                                    null=True, blank=True)
    
    class Meta:
        verbose_name = '予測'
        verbose_name_plural = '予測'
        unique_together = ['race', 'model_version']
        
    def __str__(self):
        return f"{self.race} - {self.predicted_winner.horse.name} ({self.confidence_score:.2f})"


class PredictionModel(TimeStampedModel):
    """
    予測モデル管理
    """
    name = models.CharField('モデル名', max_length=100)
    version = models.CharField('バージョン', max_length=50)
    description = models.TextField('説明', blank=True)
    
    # モデル設定
    algorithm = models.CharField('アルゴリズム', max_length=50)
    parameters = models.JSONField('パラメータ', default=dict)
    
    # 性能指標
    accuracy = models.FloatField('精度', null=True, blank=True)
    precision = models.FloatField('適合率', null=True, blank=True)
    recall = models.FloatField('再現率', null=True, blank=True)
    
    is_active = models.BooleanField('アクティブ', default=False)
    
    class Meta:
        verbose_name = '予測モデル'
        verbose_name_plural = '予測モデル'
        unique_together = ['name', 'version']
        
    def __str__(self):
        return f"{self.name} v{self.version}"
