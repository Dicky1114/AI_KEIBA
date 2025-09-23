"""
レース関連モデル
"""
from django.db import models
from apps.core.models import TimeStampedModel, RaceClass, TrackCondition, Weather


class Venue(TimeStampedModel):
    """
    競馬場モデル
    """
    name = models.CharField('競馬場名', max_length=100, unique=True)
    code = models.CharField('競馬場コード', max_length=10, unique=True)
    location = models.CharField('所在地', max_length=100)
    
    class Meta:
        verbose_name = '競馬場'
        verbose_name_plural = '競馬場'
        
    def __str__(self):
        return self.name


class Race(TimeStampedModel):
    """
    レースモデル
    """
    race_id = models.CharField('レースID', max_length=12, unique=True)
    name = models.CharField('レース名', max_length=255)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, verbose_name='競馬場')
    race_date = models.DateField('開催日')
    race_number = models.IntegerField('レース番号')
    
    # レース条件
    race_class = models.CharField('レースクラス', max_length=20, choices=RaceClass.choices)
    distance = models.IntegerField('距離（メートル）')
    track_type = models.CharField('コース種別', max_length=10, choices=[
        ('turf', '芝'),
        ('dirt', 'ダート'),
        ('jump', '障害'),
    ])
    track_condition = models.CharField('馬場状態', max_length=20, choices=TrackCondition.choices)
    weather = models.CharField('天候', max_length=20, choices=Weather.choices)
    
    # レース詳細
    start_time = models.TimeField('発走時刻')
    prize_money = models.BigIntegerField('賞金（円）', default=0)
    entry_count = models.IntegerField('出走頭数', default=0)
    
    # フラグ
    is_grade_race = models.BooleanField('重賞レース', default=False)
    is_completed = models.BooleanField('レース終了', default=False)
    
    class Meta:
        verbose_name = 'レース'
        verbose_name_plural = 'レース'
        unique_together = ['venue', 'race_date', 'race_number']
        
    def __str__(self):
        return f"{self.race_date} {self.venue.name} {self.race_number}R {self.name}"


class RaceEntry(TimeStampedModel):
    """
    出走馬エントリーモデル
    """
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name='entries')
    horse = models.ForeignKey('horses.Horse', on_delete=models.CASCADE)
    jockey = models.ForeignKey('horses.Jockey', on_delete=models.CASCADE)
    
    # 出走情報
    horse_number = models.IntegerField('馬番')
    frame_number = models.IntegerField('枠番')
    weight = models.FloatField('斤量')
    horse_weight = models.IntegerField('馬体重', null=True, blank=True)
    weight_change = models.IntegerField('馬体重増減', null=True, blank=True)
    
    # オッズ情報
    win_odds = models.FloatField('単勝オッズ', null=True, blank=True)
    place_odds = models.FloatField('複勝オッズ', null=True, blank=True)
    popularity = models.IntegerField('人気', null=True, blank=True)
    
    class Meta:
        verbose_name = '出走馬'
        verbose_name_plural = '出走馬'
        unique_together = ['race', 'horse_number']
        
    def __str__(self):
        return f"{self.race} {self.horse_number}番 {self.horse.name}"


class RaceResult(TimeStampedModel):
    """
    レース結果モデル
    """
    entry = models.OneToOneField(RaceEntry, on_delete=models.CASCADE, related_name='result')
    
    # 結果情報
    finish_position = models.IntegerField('着順')
    finish_time = models.CharField('タイム', max_length=20, blank=True)
    time_difference = models.CharField('着差', max_length=20, blank=True)
    corner_positions = models.CharField('コーナー通過順', max_length=50, blank=True)
    
    # 配当情報
    win_payout = models.IntegerField('単勝配当', null=True, blank=True)
    place_payout = models.IntegerField('複勝配当', null=True, blank=True)
    
    class Meta:
        verbose_name = 'レース結果'
        verbose_name_plural = 'レース結果'
        
    def __str__(self):
        return f"{self.entry} {self.finish_position}着"
