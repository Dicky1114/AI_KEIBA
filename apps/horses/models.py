"""
馬・騎手関連モデル
"""
from django.db import models
from apps.core.models import TimeStampedModel


class Horse(TimeStampedModel):
    """
    馬モデル
    """
    name = models.CharField('馬名', max_length=255)
    birth_date = models.DateField('生年月日')
    sex = models.CharField('性別', max_length=10, choices=[
        ('male', '牡'),
        ('female', '牝'),
        ('gelding', 'セン'),
    ])
    
    # 血統情報
    sire = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                           related_name='offspring_as_sire', verbose_name='父')
    dam = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                          related_name='offspring_as_dam', verbose_name='母')
    
    # 基本情報
    owner = models.CharField('馬主', max_length=255, blank=True)
    trainer = models.CharField('調教師', max_length=255, blank=True)
    breeder = models.CharField('生産者', max_length=255, blank=True)
    
    class Meta:
        verbose_name = '馬'
        verbose_name_plural = '馬'
        
    def __str__(self):
        return self.name


class Jockey(TimeStampedModel):
    """
    騎手モデル
    """
    name = models.CharField('騎手名', max_length=255)
    birth_date = models.DateField('生年月日', null=True, blank=True)
    debut_date = models.DateField('デビュー日', null=True, blank=True)
    
    # 所属情報
    stable = models.CharField('所属厩舎', max_length=255, blank=True)
    license_type = models.CharField('免許種別', max_length=20, choices=[
        ('flat', '平地'),
        ('jump', '障害'),
        ('both', '平地・障害'),
    ], default='flat')
    
    # 統計情報（定期的に更新）
    total_races = models.IntegerField('総騎乗数', default=0)
    total_wins = models.IntegerField('勝利数', default=0)
    win_rate = models.FloatField('勝率', default=0.0)
    
    class Meta:
        verbose_name = '騎手'
        verbose_name_plural = '騎手'
        
    def __str__(self):
        return self.name


class HorsePerformance(TimeStampedModel):
    """
    馬の成績履歴
    """
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name='performances')
    race = models.ForeignKey('races.Race', on_delete=models.CASCADE)
    
    # 成績情報
    finish_position = models.IntegerField('着順')
    finish_time = models.CharField('タイム', max_length=20, blank=True)
    jockey = models.ForeignKey(Jockey, on_delete=models.CASCADE)
    weight = models.FloatField('斤量')
    horse_weight = models.IntegerField('馬体重', null=True, blank=True)
    
    # 条件
    distance = models.IntegerField('距離')
    track_condition = models.CharField('馬場状態', max_length=20)
    
    class Meta:
        verbose_name = '馬成績'
        verbose_name_plural = '馬成績'
        unique_together = ['horse', 'race']
        
    def __str__(self):
        return f"{self.horse.name} - {self.race.name} {self.finish_position}着"
