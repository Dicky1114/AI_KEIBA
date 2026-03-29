from django.db import models
from django.contrib.auth.models import AbstractUser

# テーブルクラス
class CustomUser(AbstractUser):
    def __str__(self):
        return self.username
    
class PlaceMst(models.Model):
    class Meta:
        db_table = 'm_place'
        ordering = ['place_id']
        
    # エクスポート機能がうまく動作しないため手動で追加
    id = models.AutoField(primary_key=True)
    place_id = models.CharField(max_length=2, db_comment="場所コード", help_text="場所コード") 
    place_name = models.CharField(db_comment="場所名称", help_text="場所名称") 

    def __str__(self):
        return f"{self.place_name}"

# スクレイピング情報
class URLMst(models.Model):
    class Meta:
        db_table = 'm_url'
        ordering = ['race_date', 'race_id']
        verbose_name = "URL情報"
        verbose_name_plural = "URL情報一覧"

    # エクスポート機能がうまく動作しないため手動で追加
    id = models.AutoField(primary_key=True)
    race_id = models.CharField(max_length=12, db_comment="レースID", help_text="レースID") 
    race_date = models.DateTimeField(db_comment="レース日付", help_text="レース日付") 
    url = models.CharField(db_comment="URL", help_text="URL")
    
    created_at = models.DateTimeField(db_comment="作成日時", help_text="作成日時")  
    updated_at = models.DateTimeField(db_comment="更新日時", help_text="更新日時")  

    created_user = models.CharField(max_length=255, null=True, db_comment="作成ユーザーID", help_text="作成ユーザーID")  
    updated_user = models.CharField(max_length=255, null=True, db_comment="更新ユーザーID", help_text="更新ユーザーID")  
    def __str__(self):
        return f"{self.race_id} - {self.url}"

class BaseData(models.Model):
    class Meta:
        db_table = 't_base_info'
        constraints = [
            models.UniqueConstraint(fields=['race_id', 'horse_number'], name='unique_base_info')
        ]
        ordering = ['race_date', 'race_date', 'horse_number']
        verbose_name = "レース情報"
        verbose_name_plural = "レース情報一覧"

    race_id = models.CharField(max_length=12, db_comment="レースID", help_text="レースID") 
    horse_number = models.CharField(max_length=5, db_comment="馬番", help_text="馬番")
    horse_name = models.CharField(max_length=255, db_comment="馬名", help_text="馬名")
    race_date = models.DateField(db_comment="レース日付", null=True, blank=True, help_text="レース日付") 
    event_title = models.CharField(max_length=255, null=True, db_comment="レース名", help_text="レース名") 
    frame_number = models.CharField(max_length=5,  null=True, db_comment="枠番号", help_text="枠番号")  
    sex = models.CharField(max_length=10, null=True, db_comment="性別", help_text="性別") 
    weight = models.CharField(null=True, db_comment="斤量", help_text="斤量") 
    body_weight = models.CharField(null=True, db_comment="馬体重", help_text="馬体重")  
    jockey_name = models.CharField(max_length=255, null=True, db_comment="騎手名", help_text="騎手名")  
    stable_name = models.CharField(max_length=255, null=True, db_comment="厩舎名", help_text="厩舎名")
    odds = models.CharField(null=True, db_comment="オッズ", help_text="オッズ")  
    popularity = models.CharField(null=True, db_comment="人気順", help_text="人気順")  

    new_flg = models.BooleanField(default=False, db_comment="新馬戦フラグ", help_text="新馬戦フラグ")  
    not_win_flg = models.BooleanField(default=False, db_comment="未勝利戦フラグ", help_text="未勝利戦フラグ")  
    win_1_flg = models.BooleanField(default=False, db_comment="1勝フラグ", help_text="1勝フラグ")  
    win_2_flg = models.BooleanField(default=False, db_comment="2勝フラグ", help_text="2勝フラグ")  
    win_3_flg = models.BooleanField(default=False, db_comment="3勝フラグ", help_text="3勝フラグ")  
    g3_flg = models.BooleanField(default=False, db_comment="G3フラグ", help_text="G3フラグ")  
    g2_flg = models.BooleanField(default=False, db_comment="G2フラグ", help_text="G2フラグ")  
    g1_flg = models.BooleanField(default=False, db_comment="G1フラグ", help_text="G1フラグ")  
    l_flg = models.BooleanField(default=False, db_comment="Lクラスフラグ", help_text="Lクラスフラグ")  
    op_flg = models.BooleanField(default=False, db_comment="OPクラスフラグ", help_text="OPクラスフラグ")  
    is_win5 = models.BooleanField(default=False, db_comment="Win5対象フラグ", help_text="Win5対象フラグ")  

    race_place = models.CharField(null=True, max_length=255, db_comment="開催場所", help_text="開催場所")   
    horse_url = models.CharField(null=True, db_comment="馬URL", help_text="馬URL")
    jockey_url = models.CharField(null=True, db_comment="騎手URL", help_text="騎手URL")
    
    distance = models.CharField(null=True, max_length=255, db_comment="距離", help_text="距離")   
    weather = models.CharField(null=True, db_comment="天気", help_text="天気")
    track_condition = models.CharField(null=True, db_comment="馬場", help_text="馬場")
    count = models.CharField(null=True, db_comment="頭数", help_text="頭数")
    race_place = models.CharField(null=True, db_comment="競技場", help_text="競技場")
    created_at = models.DateTimeField(db_comment="作成日時", help_text="作成日時")  
    updated_at = models.DateTimeField(db_comment="更新日時", help_text="更新日時")  

    created_user = models.CharField(max_length=255, null=True, db_comment="作成ユーザーID", help_text="作成ユーザーID")  
    updated_user = models.CharField(max_length=255, null=True, db_comment="更新ユーザーID", help_text="更新ユーザーID")  

    def __str__(self):
        return f"{self.race_id} - {self.horse_name}"

class ResultData(models.Model):
    class Meta:
        db_table = 't_result_info' 
        constraints = [
            models.UniqueConstraint(fields=['race_id', 'horse_number'], name='unique_result_info')
        ]
        ordering = ['race_date', 'race_date', 'horse_number']
        verbose_name = "レース(結果)情報"
        verbose_name_plural = "レース(結果)情報一覧"

    # エクスポート機能がうまく動作しないため手動で追加
    id = models.AutoField(primary_key=True)
    race_id = models.CharField(max_length=12, db_comment="レースID", help_text="レースID")  
    horse_number = models.CharField(max_length=5,  db_comment="馬番", help_text="馬番")  
    horse_name = models.CharField(max_length=255, db_comment="馬名", help_text="馬名")  
    rank = models.CharField(max_length=10, db_comment="着順", help_text="着順")  
    race_time = models.CharField(max_length=20, db_comment="タイム", help_text="タイム")  
    corner_order = models.CharField(max_length=50, db_comment="コーナー通過順", help_text="コーナー通過順")  
    race_date = models.DateField(db_comment="レース日付", null=True, blank=True, help_text="レース日付")  
    positions = models.CharField(max_length=10, default='', db_comment="レース順位", help_text="レース順位") 
    positions_tie = models.CharField(max_length=10, null=True, db_comment="同率レース順位", help_text="同率レース順位") 
    pay1 = models.CharField(max_length=30, default='', db_comment="単勝", help_text="単勝")
    pay1_tie = models.CharField(max_length=30, null=True, db_comment="同率単勝", help_text="同率単勝")  
    pay123_1 = models.CharField(max_length=30, default='', db_comment="複勝1", help_text="複勝1")  
    pay123_2 = models.CharField(max_length=30, default='', db_comment="複勝2", help_text="複勝2")  
    pay123_3 = models.CharField(max_length=30, default='', db_comment="複勝1", help_text="複勝1")
    pay123_tie = models.CharField(max_length=30,  null=True, db_comment="同率複勝1", help_text="同率複勝1")  
    pay123_12_1 = models.CharField(max_length=30, default='', db_comment="ワイド1", help_text="ワイド1")  
    pay123_12_2 = models.CharField(max_length=30, default='', db_comment="ワイド2", help_text="ワイド2")  
    pay123_12_3 = models.CharField(max_length=30, default='', db_comment="ワイド3", help_text="ワイド3") 
    pay123_12_4_tie = models.CharField(max_length=30,  null=True, db_comment="同率ワイド2", help_text="同率ワイド2")  
    pay123_12_5_tie = models.CharField(max_length=30,  null=True, db_comment="同率ワイド3", help_text="同率ワイド3")   
    pay12_21 = models.CharField(max_length=30, default='', db_comment="馬連", help_text="馬連")  
    pay12_21_tie = models.CharField(max_length=30,  null=True, db_comment="同率馬連", help_text="同率馬連")  
    pay12_12 = models.CharField(max_length=30, default='', db_comment="馬単", help_text="馬単")  
    pay12_12_tie = models.CharField(max_length=30,  null=True, db_comment="同率馬単", help_text="同率馬単")  
    pay123_321 = models.CharField(max_length=30, default='', db_comment="3連複", help_text="3連複")  
    pay123_321_tie = models.CharField(max_length=30,  null=True, db_comment="同率3連複", help_text="同率3連複")  
    pay123_123 = models.CharField(max_length=30, default='', db_comment="3連単", help_text="3連単")  
    pay123_123_tie = models.CharField(max_length=30,  null=True, db_comment="同率3連単", help_text="同率3連単")  

    created_at = models.DateTimeField(db_comment="作成日時", help_text="作成日時")  
    updated_at = models.DateTimeField(db_comment="更新日時", help_text="更新日時")  
    created_user = models.CharField(max_length=255, null=True, db_comment="作成ユーザーID", help_text="作成ユーザーID")  
    updated_user = models.CharField(max_length=255, null=True, db_comment="更新ユーザーID", help_text="更新ユーザーID")  

    def __str__(self):
        return f"{self.race_id} - {self.horse_name} - {self.rank}"

class HorseData(models.Model):
    class Meta:
        db_table = 't_horse_info'
        verbose_name = "馬情報"
        verbose_name_plural = "馬情報一覧"

    id = models.AutoField(primary_key=True)
    horse_id = models.CharField(max_length=20, db_comment="馬ID", help_text="馬ID")
    horse_name = models.CharField(max_length=255, db_comment='馬名', help_text='馬名')

    race_date = models.CharField(db_comment='レース日付', null=True, blank=True, help_text='レース日付')
    race_place = models.CharField(max_length=255, db_comment='開催場所', null=True, blank=True, help_text='開催場所')
    weather = models.CharField(max_length=50, db_comment='天候', null=True, blank=True, help_text='天候')
    race_name = models.CharField(max_length=255, db_comment='レース名', null=True, blank=True, help_text='レース名')
    count = models.CharField(max_length=5, db_comment='頭数', null=True, blank=True, help_text='頭数')
    frame = models.CharField(max_length=5, db_comment='枠番号', null=True, blank=True, help_text='枠番号')
    horse_number = models.CharField(max_length=5, db_comment='馬番', null=True, blank=True, help_text='馬番')
    odds = models.CharField(db_comment='オッズ', null=True, blank=True, help_text='オッズ')
    popularity = models.CharField(max_length=5, db_comment='人気順', null=True, blank=True, help_text='人気順')
    rank = models.CharField(max_length=5, db_comment='順位', null=True, blank=True, help_text='順位')
    jockey = models.CharField(max_length=255, db_comment='騎手名', null=True, blank=True, help_text='騎手名')
    weight = models.CharField(db_comment='斤量', null=True, blank=True, help_text='斤量')
    distance = models.CharField(db_comment='距離', null=True, blank=True, help_text='距離')
    track_condition = models.CharField(max_length=50, db_comment='コース状態', null=True, blank=True, help_text='コース状態')
    time = models.CharField(max_length=20, db_comment='タイム', null=True, blank=True, help_text='タイム')
    time_diff = models.CharField(db_comment='着差', null=True, blank=True, help_text='着差')
    position = models.CharField(max_length=20, db_comment='通過', null=True, blank=True, help_text='通過')
    pace = models.CharField(max_length=20, db_comment='ペース', null=True, blank=True, help_text='ペース')
    up = models.CharField(db_comment='上り', null=True, blank=True, help_text='上り')
    body_weight = models.CharField(max_length=10, db_comment='体重', null=True, blank=True, help_text='体重')
    winner = models.CharField(max_length=255, db_comment='勝ち馬', null=True, blank=True, help_text='勝ち馬')
    prize = models.CharField(db_comment='賞金', null=True, blank=True, help_text='賞金')
    new_flg = models.BooleanField(default=False, db_comment='新馬戦フラグ', help_text='新馬戦フラグ')
    win_1_flg = models.BooleanField(default=False, db_comment='1着フラグ', help_text='1着フラグ')
    win_2_flg = models.BooleanField(default=False, db_comment='2着フラグ', help_text='2着フラグ')
    win_3_flg = models.BooleanField(default=False, db_comment='3着フラグ', help_text='3着フラグ')
    not_win_flg = models.BooleanField(default=False, db_comment='未勝利フラグ', help_text='未勝利フラグ')
    g3_flg = models.BooleanField(default=False, db_comment='G3フラグ', help_text='G3フラグ')
    g2_flg = models.BooleanField(default=False, db_comment='G2フラグ', help_text='G2フラグ')
    g1_flg = models.BooleanField(default=False, db_comment='G1フラグ', help_text='G1フラグ')
    l_flg = models.BooleanField(default=False, db_comment='lフラグ', help_text='lフラグ')
    op_flg = models.BooleanField(default=False, db_comment='opフラグ', help_text='opフラグ')

    created_at = models.DateTimeField(db_comment="作成日時", help_text="作成日時")  
    updated_at = models.DateTimeField(db_comment="更新日時", help_text="更新日時")  
    created_user = models.CharField(max_length=255, null=True, db_comment="作成ユーザーID", help_text="作成ユーザーID")  
    updated_user = models.CharField(max_length=255, null=True, db_comment="更新ユーザーID", help_text="更新ユーザーID")  

    def __str__(self):
        return f'{self.horse_id} - {self.horse_name}'
    
class JockeyData(models.Model):
    class Meta:
        db_table = 't_jockey_info'
        verbose_name = "騎手情報"
        verbose_name_plural = "騎手情報一覧"

    id = models.AutoField(primary_key=True)
    jockey_id = models.CharField(max_length=20, db_comment="騎手ID", help_text="騎手ID")
    jockey_name = models.CharField(max_length=255, db_comment='騎手名', help_text='騎手名')

    race_date = models.CharField(db_comment='レース日付', null=True, blank=True, help_text='レース日付')
    race_place = models.CharField(max_length=255, db_comment='開催場所', null=True, blank=True, help_text='開催場所')
    weather = models.CharField(max_length=50, db_comment='天候', null=True, blank=True, help_text='天候')
    race = models.CharField(db_comment='レース目', null=True, blank=True, help_text='レース目')
    race_name = models.CharField(max_length=255, db_comment='レース名', null=True, blank=True, help_text='レース名')
    count = models.CharField(max_length=5, db_comment='頭数', null=True, blank=True, help_text='頭数')
    frame = models.CharField(max_length=5, db_comment='枠番号', null=True, blank=True, help_text='枠番号')
    horse_number = models.CharField(max_length=5, db_comment='馬番', null=True, blank=True, help_text='馬番')
    odds = models.CharField(db_comment='オッズ', null=True, blank=True, help_text='オッズ')
    popularity = models.CharField(max_length=5, db_comment='人気順', null=True, blank=True, help_text='人気順')
    rank = models.CharField(max_length=5, db_comment='順位', null=True, blank=True, help_text='順位')
    horse = models.CharField(max_length=255, db_comment='馬名', null=True, blank=True, help_text='馬名')
    weight = models.CharField(db_comment='斤量', null=True, blank=True, help_text='斤量')
    distance = models.CharField(db_comment='距離', null=True, blank=True, help_text='距離')
    track_condition = models.CharField(max_length=50, db_comment='コース状態', null=True, blank=True, help_text='コース状態')
    time = models.CharField(max_length=20, db_comment='タイム', null=True, blank=True, help_text='タイム')
    time_diff = models.CharField(db_comment='着差', null=True, blank=True, help_text='着差')
    position = models.CharField(max_length=20, db_comment='通過', null=True, blank=True, help_text='通過')
    pace = models.CharField(max_length=20, db_comment='ペース', null=True, blank=True, help_text='ペース')
    up = models.CharField(db_comment='上り', null=True, blank=True, help_text='上り')
    body_weight = models.CharField(max_length=10, db_comment='体重', null=True, blank=True, help_text='体重')
    winner = models.CharField(max_length=255, db_comment='勝ち馬', null=True, blank=True, help_text='勝ち馬')
    prize = models.CharField(db_comment='賞金', null=True, blank=True, help_text='賞金')
    new_flg = models.BooleanField(default=False, db_comment='新馬戦フラグ', help_text='新馬戦フラグ')
    win_1_flg = models.BooleanField(default=False, db_comment='1着フラグ', help_text='1着フラグ')
    win_2_flg = models.BooleanField(default=False, db_comment='2着フラグ', help_text='2着フラグ')
    win_3_flg = models.BooleanField(default=False, db_comment='3着フラグ', help_text='3着フラグ')
    not_win_flg = models.BooleanField(default=False, db_comment='未勝利フラグ', help_text='未勝利フラグ')
    g3_flg = models.BooleanField(default=False, db_comment='G3フラグ', help_text='G3フラグ')
    g2_flg = models.BooleanField(default=False, db_comment='G2フラグ', help_text='G2フラグ')
    g1_flg = models.BooleanField(default=False, db_comment='G1フラグ', help_text='G1フラグ')
    l_flg = models.BooleanField(default=False, db_comment='lフラグ', help_text='lフラグ')
    op_flg = models.BooleanField(default=False, db_comment='opフラグ', help_text='opフラグ')

    created_at = models.DateTimeField(db_comment="作成日時", help_text="作成日時")  
    updated_at = models.DateTimeField(db_comment="更新日時", help_text="更新日時")  
    created_user = models.CharField(max_length=255, null=True, db_comment="作成ユーザーID", help_text="作成ユーザーID")  
    updated_user = models.CharField(max_length=255, null=True, db_comment="更新ユーザーID", help_text="更新ユーザーID")  

    def __str__(self):
        return f'{self.jockey_id} - {self.jockey_name}'

# スクレイピング情報（加工）
class FinalBaseInfo(models.Model):
    class Meta:
        db_table = 't_final_base_info'
        unique_together = ('race_id', 'horse_id', 'jockey_id')
        verbose_name = '最終ベース情報'
        verbose_name_plural = '最終ベース情報一覧'

    race_id = models.CharField(max_length=12, db_column='RACE_ID', help_text='レースID')
    today_race_date = models.DateField(db_column='TODAY_RACE_DATE', help_text='当日レース日付')
    today_race_no = models.SmallIntegerField(db_column='TODAY_RACE_NO', help_text='当日レース番号')
    place_id = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID', help_text='開催地ID')
    place_name = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME', help_text='開催地名')
    horse_id = models.CharField(max_length=10, null=True, blank=True, db_column='HORSE_ID', help_text='馬ID')
    horse = models.CharField(max_length=20, null=True, blank=True, db_column='HORSE', help_text='馬名')
    frame_number = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER', help_text='枠番')
    horse_number = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER', help_text='馬番')
    sex = models.CharField(max_length=5, null=True, blank=True, db_column='SEX', help_text='性別')
    age = models.SmallIntegerField(null=True, blank=True, db_column='AGE', help_text='年齢')
    weight = models.SmallIntegerField(null=True, blank=True, db_column='WEIGHT', help_text='斤量')
    body_weight = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT', help_text='馬体重')
    jockey_id = models.CharField(max_length=5, null=True, blank=True, db_column='JOCKEY_ID', help_text='騎手ID')
    jockey = models.CharField(max_length=20, null=True, blank=True, db_column='JOCKEY', help_text='騎手名')
    
    weight_4kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_4KG_CUT_FLG')
    weight_3kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_3KG_CUT_FLG')
    weight_2kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_2KG_CUT_FLG')
    weight_1kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_1KG_CUT_FLG')
    women_weight_2kg_cut_flg = models.BooleanField(default=False, db_column='WOMEN_WEIGHT_2KG_CUT_FLG')

    stable_name = models.CharField(max_length=20, null=True, blank=True, db_column='STABLE_NAME', help_text='厩舎名')
    odds = models.FloatField(null=True, blank=True, db_column='ODDS', help_text='オッズ')
    popularity = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY', help_text='人気順')

    new_flg = models.BooleanField(default=False, db_column='NEW_FLG')
    g1_flg = models.BooleanField(default=False, db_column='G1_FLG')
    g2_flg = models.BooleanField(default=False, db_column='G2_FLG')
    g3_flg = models.BooleanField(default=False, db_column='G3_FLG')
    l_flg = models.BooleanField(default=False, db_column='L_FLG')
    not_win_flg = models.BooleanField(default=False, db_column='NOT_WIN_FLG')
    op_flg = models.BooleanField(default=False, db_column='OP_FLG')

    win_1_flg = models.BooleanField(default=False, db_column='WIN_1_FLG')
    win_2_flg = models.BooleanField(default=False, db_column='WIN_2_FLG')
    win_3_flg = models.BooleanField(default=False, db_column='WIN_3_FLG')
    is_win5 = models.BooleanField(default=False, db_column='IS_WIN5')

    def __str__(self):
        return f"{self.race_id} - {self.horse} ({self.horse_number})"

class FinalHorseInfo(models.Model):
    class Meta:
        db_table = 't_final_horse_info'
        verbose_name = '最終馬情報'
        verbose_name_plural = '最終馬情報一覧'
        unique_together = ('today_race_date', 'history_race_date', 'horse_id', 'jockey')

    today_race_date = models.DateField(db_column='TODAY_RACE_DATE', help_text='当日レース日')
    history_race_date = models.DateField(null=True, blank=True, db_column='RACE_DATE', help_text='過去レース日')
    race_name = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME', help_text='レース名')
    track_condition = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION', help_text='馬場状態')
    weather = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER', help_text='天気')
    place_id = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID', help_text='開催地ID')
    place_name = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME', help_text='開催地名')
    count = models.SmallIntegerField(null=True, blank=True, db_column='COUNT', help_text='頭数')
    field = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD', help_text='競馬場の場別')
    distance = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE', help_text='距離(m)')
    horse_id = models.CharField(max_length=10, null=True, blank=True, db_column='HORSE_ID', help_text='馬ID')
    body_weight = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT', help_text='馬体重')
    frame_number = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER', help_text='枠番')
    horse_number = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER', help_text='馬番')
    jockey = models.CharField(max_length=20, null=True, blank=True, db_column='JOCKEY', help_text='騎手名')
    rank = models.SmallIntegerField(null=True, blank=True, db_column='RANK', help_text='着順')
    time = models.FloatField(null=True, blank=True, db_column='TIME', help_text='タイム')
    time_diff = models.FloatField(null=True, blank=True, db_column='TIME_DIFF', help_text='着差')
    time_up = models.FloatField(null=True, blank=True, db_column='TIME_UP', help_text='上がりタイム')
    pace_1 = models.FloatField(null=True, blank=True, db_column='PACE_1', help_text='前半ペース')
    pace_2 = models.FloatField(null=True, blank=True, db_column='PACE_2', help_text='後半ペース')
    position_1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1')
    position_2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2')
    position_3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3')
    position_4 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4')
    odds = models.FloatField(null=True, blank=True, db_column='ODDS')
    popularity = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY')
    winner = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER')
    prize = models.IntegerField(null=True, blank=True, db_column='PRIZE')

    new_flg = models.BooleanField(default=False, db_column='NEW_FLG')
    g1_flg = models.BooleanField(default=False, db_column='G1_FLG')
    g2_flg = models.BooleanField(default=False, db_column='G2_FLG')
    g3_flg = models.BooleanField(default=False, db_column='G3_FLG')
    l_flg = models.BooleanField(default=False, db_column='L_FLG')
    not_win_flg = models.BooleanField(default=False, db_column='NOT_WIN_FLG')
    op_flg = models.BooleanField(default=False, db_column='OP_FLG')
    win_1_flg = models.BooleanField(default=False, db_column='WIN_1_FLG')
    win_2_flg = models.BooleanField(default=False, db_column='WIN_2_FLG')
    win_3_flg = models.BooleanField(default=False, db_column='WIN_3_FLG')

    gr_id = models.SmallIntegerField(db_column='GR_ID', help_text='グループID')

    def __str__(self):
        return f"{self.horse_id} - {self.race_name} ({self.today_race_date})"

class FinalJockeyInfo(models.Model):
    class Meta:
        db_table = 't_final_jockey_info'
        verbose_name = '最終騎手情報'
        verbose_name_plural = '最終騎手情報一覧'
        unique_together = ('today_race_date', 'today_race_no', 'history_race_date', 'history_race_no', 'horse', 'jockey_id')


    today_race_date = models.DateField(db_column='TODAY_RACE_DATE', help_text='当日レース日')
    today_race_no = models.SmallIntegerField(db_column='TODAY_RACE_NO', help_text='当日レース番号')
    history_race_date = models.DateField(null=True, blank=True, db_column='RACE_DATE', help_text='過去レース日')
    history_race_no = models.SmallIntegerField(null=True, blank=True, db_column='RACE_NO', help_text='過去レース番号')
    race_name = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME', help_text='レース名')
    track_condition = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION', help_text='馬場状態')
    weather = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER', help_text='天気')
    place_id = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID', help_text='開催地ID')
    place_name = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME', help_text='開催地名')
    count = models.SmallIntegerField(null=True, blank=True, db_column='COUNT', help_text='頭数')
    field = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD', help_text='場別')
    distance = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE', help_text='距離(m)')

    jockey_id = models.CharField(max_length=5, db_column='JOCKEY_ID', help_text='騎手ID')
    body_weight = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT', help_text='馬体重')
    weight = models.SmallIntegerField(null=True, blank=True, db_column='WEIGHT', help_text='斤量')
    frame_number = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER', help_text='枠番')
    horse_number = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER', help_text='馬番')
    horse = models.CharField(max_length=20, null=True, blank=True, db_column='HORSE', help_text='馬名')

    rank = models.SmallIntegerField(null=True, blank=True, db_column='RANK', help_text='着順')
    time = models.FloatField(null=True, blank=True, db_column='TIME', help_text='タイム')
    time_diff = models.FloatField(null=True, blank=True, db_column='TIME_DIFF', help_text='着差')
    time_up = models.FloatField(null=True, blank=True, db_column='TIME_UP', help_text='上がりタイム')

    pace_1 = models.FloatField(null=True, blank=True, db_column='PACE_1', help_text='前半ペース')
    pace_2 = models.FloatField(null=True, blank=True, db_column='PACE_2', help_text='後半ペース')

    position_1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1')
    position_2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2')
    position_3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3')
    position_4 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4')

    odds = models.FloatField(null=True, blank=True, db_column='ODDS', help_text='オッズ')
    popularity = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY', help_text='人気')

    winner = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER', help_text='勝ち馬名')
    prize = models.IntegerField(null=True, blank=True, db_column='PRIZE', help_text='賞金')

    weight_4kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_4KG_CUT_FLG')
    weight_3kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_3KG_CUT_FLG')
    weight_2kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_2KG_CUT_FLG')
    weight_1kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_1KG_CUT_FLG')
    women_weight_2kg_cut_flg = models.BooleanField(default=False, db_column='WOMEN_WEIGHT_2KG_CUT_FLG')

    new_flg = models.BooleanField(default=False, db_column='NEW_FLG')
    g1_flg = models.BooleanField(default=False, db_column='G1_FLG')
    g2_flg = models.BooleanField(default=False, db_column='G2_FLG')
    g3_flg = models.BooleanField(default=False, db_column='G3_FLG')
    l_flg = models.BooleanField(default=False, db_column='L_FLG')
    not_win_flg = models.BooleanField(default=False, db_column='NOT_WIN_FLG')
    op_flg = models.BooleanField(default=False, db_column='OP_FLG')
    win_1_flg = models.BooleanField(default=False, db_column='WIN_1_FLG')
    win_2_flg = models.BooleanField(default=False, db_column='WIN_2_FLG')
    win_3_flg = models.BooleanField(default=False, db_column='WIN_3_FLG')

    gr_id = models.SmallIntegerField(db_column='GR_ID', help_text='グループID')

    def __str__(self):
        return f"{self.jockey_id} - {self.today_race_date} R{self.today_race_no}"

class FinalResultInfo(models.Model):
    class Meta:
        db_table = 't_final_result_info'
        verbose_name = '最終結果情報'
        verbose_name_plural = '最終結果情報一覧'
        unique_together = ('race_id', 'horse_number')

    race_id = models.CharField(max_length=12, db_column='RACE_ID', help_text='レースID')
    horse_number = models.SmallIntegerField(db_column='HORSE_NUMBER', help_text='馬番号')
    rank = models.SmallIntegerField(db_column='RANK', help_text='着順')

    race_time = models.FloatField(null=True, blank=True, db_column='RACE_TIME', help_text='レースタイム')
    corner_order = models.CharField(max_length=20, null=True, blank=True, db_column='CORNER_ORDER', help_text='コーナー順')
    positions = models.CharField(max_length=10, null=True, blank=True, db_column='POSITIONS', help_text='走行位置')
    positions_tie = models.CharField(max_length=10, null=True, blank=True, db_column='POSITIONS_TIE', help_text='同着位置')

    pay1 = models.IntegerField(null=True, blank=True, db_column='PAY1', help_text='単勝払戻')
    pay1_tie = models.IntegerField(null=True, blank=True, db_column='PAY1_TIE', help_text='単勝同着払戻')

    pay123_1 = models.IntegerField(null=True, blank=True, db_column='PAY123_1', help_text='3連単 1番目')
    pay123_2 = models.IntegerField(null=True, blank=True, db_column='PAY123_2', help_text='3連単 2番目')
    pay123_3 = models.IntegerField(null=True, blank=True, db_column='PAY123_3', help_text='3連単 3番目')
    pay123_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_TIE', help_text='3連単 同着')

    pay123_12_1 = models.IntegerField(null=True, blank=True, db_column='PAY123_12_1')
    pay123_12_2 = models.IntegerField(null=True, blank=True, db_column='PAY123_12_2')
    pay123_12_3 = models.IntegerField(null=True, blank=True, db_column='PAY123_12_3')
    pay123_12_4_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_12_4_TIE')
    pay123_12_5_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_12_5_TIE')

    pay12_21 = models.IntegerField(null=True, blank=True, db_column='PAY12_21')
    pay12_21_tie = models.IntegerField(null=True, blank=True, db_column='PAY12_21_TIE')
    pay12_12 = models.IntegerField(null=True, blank=True, db_column='PAY12_12')
    pay12_12_tie = models.IntegerField(null=True, blank=True, db_column='PAY12_12_TIE')

    pay123_321 = models.IntegerField(null=True, blank=True, db_column='PAY123_321')
    pay123_321_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_321_TIE')
    pay123_123 = models.IntegerField(null=True, blank=True, db_column='PAY123_123')
    pay123_123_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_123_TIE')

    def __str__(self):
        return f"{self.race_id} - 着順 {self.rank}"

# 学習データ（加工）
class TrainingInfo(models.Model):
    class Meta:
        db_table = 't_training'
        verbose_name = '学習データ'
        verbose_name_plural = '学習データ一覧'
        unique_together = ('race_id', 'horse_id', 'jockey_id')
  
    # メインレース
    race_id = models.CharField(max_length=12, db_column='RACE_ID_TODAY', help_text='レースID', verbose_name='【当日】レースID')
    today_race_date = models.DateField(db_column='RACE_DATE_TODAY', help_text='当日レース日付', verbose_name='【当日】レース日付')
    today_race_no = models.SmallIntegerField(db_column='RACE_NO_TODAY', help_text='当日レース番号', verbose_name='【当日】レース番号')
    place_id = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID_TODAY', help_text='開催地ID', verbose_name='【当日】開催地ID')
    place_name = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME_TODAY', help_text='開催地名', verbose_name='【当日】開催地名')
    horse_id = models.CharField(max_length=10, null=True, blank=True, db_column='HORSE_ID_TODAY', help_text='馬ID', verbose_name='【当日】馬ID')
    horse = models.CharField(max_length=20, null=True, blank=True, db_column='HORSE_TODAY', help_text='馬名', verbose_name='【当日】馬名')
    frame_number = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER_TODAY', help_text='枠番', verbose_name='【当日】枠番')
    horse_number = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER_TODAY', help_text='馬番', verbose_name='【当日】馬番')
    sex = models.CharField(max_length=5, null=True, blank=True, db_column='SEX_TODAY', help_text='性別', verbose_name='【当日】性別')
    age = models.SmallIntegerField(null=True, blank=True, db_column='AGE_TODAY', help_text='年齢', verbose_name='【当日】年齢')
    weight = models.SmallIntegerField(null=True, blank=True, db_column='WEIGHT_TODAY', help_text='斤量', verbose_name='【当日】斤量')
    body_weight = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT_TODAY', help_text='馬体重', verbose_name='【当日】馬体重')
    jockey_id = models.CharField(max_length=5, null=True, blank=True, db_column='JOCKEY_ID_TODAY', help_text='騎手ID', verbose_name='【当日】騎手ID')
    jockey = models.CharField(max_length=20, null=True, blank=True, db_column='JOCKEY_TODAY', help_text='騎手名', verbose_name='【当日】騎手名')
    
    weight_4kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_4KG_CUT_FLG_TODAY', verbose_name='【当日】ハンデ4KG')
    weight_3kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_3KG_CUT_FLG_TODAY', verbose_name='【当日】ハンデ3KG')
    weight_2kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_2KG_CUT_FLG_TODAY', verbose_name='【当日】ハンデ2KG')
    weight_1kg_cut_flg = models.BooleanField(default=False, db_column='WEIGHT_1KG_CUT_FLG_TODAY', verbose_name='【当日】ハンデ1KG')
    women_weight_2kg_cut_flg = models.BooleanField(default=False, db_column='WOMEN_WEIGHT_2KG_CUT_FLG_TODAY', verbose_name='【当日】女性ハンデ2KG')

    stable_name = models.CharField(max_length=20, null=True, blank=True, db_column='STABLE_NAME_TODAY', help_text='厩舎名', verbose_name='【当日】厩舎名')
    odds = models.FloatField(null=True, blank=True, db_column='ODDS_TODAY', help_text='オッズ', verbose_name='【当日】単勝オッズ')
    popularity = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY_TODAY', help_text='人気順', verbose_name='【当日】人気')

    new_flg = models.BooleanField(default=False, db_column='NEW_FLG_TODAY', verbose_name='【当日】新馬戦')
    g1_flg = models.BooleanField(default=False, db_column='G1_FLG_TODAY', verbose_name='【当日】G1戦')
    g2_flg = models.BooleanField(default=False, db_column='G2_FLG_TODAY', verbose_name='【当日】G2戦')
    g3_flg = models.BooleanField(default=False, db_column='G3_FLG_TODAY', verbose_name='【当日】G3戦')
    l_flg = models.BooleanField(default=False, db_column='L_FLG_TODAY', verbose_name='【当日】リステッド戦')
    not_win_flg = models.BooleanField(default=False, db_column='NOT_WIN_FLG_TODAY', verbose_name='【当日】未勝利戦')
    op_flg = models.BooleanField(default=False, db_column='OP_FLG_TODAY', verbose_name='【当日】オープン戦')

    win_1_flg = models.BooleanField(default=False, db_column='WIN_1_FLG_TODAY', verbose_name='【当日】1勝馬戦')
    win_2_flg = models.BooleanField(default=False, db_column='WIN_2_FLG_TODAY', verbose_name='【当日】2勝馬戦')
    win_3_flg = models.BooleanField(default=False, db_column='WIN_3_FLG_TODAY', verbose_name='【当日】3勝馬戦')
    is_win5 = models.BooleanField(default=False, db_column='IS_WIN5_TODAY', verbose_name='【当日】WIN5戦')

    # 過去馬レース１
    history_race_date_hh1 = models.DateField(null=True, blank=True, db_column='RACE_DATE_H_H_HISTORY1', help_text='過去レース日_履歴1(馬)', verbose_name='【過去履歴1】レース日(馬)')
    race_name_hh1 = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME_H_HISTORY1', help_text='レース名_履歴1(馬)', verbose_name='【過去履歴1】レース名(馬)')
    place_id_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID_H_HISTORY1', help_text='開催地ID_履歴1(馬)', verbose_name='【過去履歴1】開催地ID(馬)')
    place_name_hh1 = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME_H_HISTORY1', help_text='開催地名_履歴1(馬)', verbose_name='【過去履歴1】開催地名(馬)')
    track_condition_hh1 = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION_H_HISTORY1', help_text='馬場_履歴1(馬)', verbose_name='【過去履歴1】馬場(馬)')
    weather_hh1 = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER_H_HISTORY1', help_text='天気_履歴1(馬)', verbose_name='【過去履歴1】天気(馬)')
    count_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='COUNT_H_HISTORY1', help_text='頭数_履歴1(馬)', verbose_name='【過去履歴1】頭数(馬)')
    field_hh1 = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD_H_HISTORY1', help_text='場別_履歴1(馬)', verbose_name='【過去履歴1】場別(馬)')
    distance_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE_H_HISTORY1', help_text='距離(m)_履歴1(馬)', verbose_name='【過去履歴1】距離(m)(馬)')
    frame_number_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER_H_HISTORY1', help_text='枠番_履歴1(馬)', verbose_name='【過去履歴1】枠番(馬)')
    horse_number_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER_H_HISTORY1', help_text='馬番_履歴1(馬)', verbose_name='【過去履歴1】馬番(馬)')
    body_weight_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT_H_HISTORY1', help_text='馬体重_履歴1(馬)', verbose_name='【過去履歴1】馬体重(馬)')
    jockey_hh1 = models.CharField(max_length=20, null=True, blank=True, db_column='JOCKEY_H_HISTORY1', help_text='騎手名_履歴1(馬)', verbose_name='【過去履歴1】騎手名(馬)')
    odds_hh1 = models.FloatField(null=True, blank=True, db_column='ODDS_H_HISTORY1', help_text='オッズ_履歴1(馬)', verbose_name='【過去履歴1】単勝オッズ(馬)')
    popularity_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY_H_HISTORY1', help_text='人気_履歴1(馬)', verbose_name='【過去履歴1】人気(馬)')
    rank_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='RANK_H_HISTORY1', help_text='着順_履歴1(馬)', verbose_name='【過去履歴1】着順(馬)')
    time_hh1 = models.FloatField(null=True, blank=True, db_column='TIME_H_HISTORY1', help_text='タイム_履歴1(馬)', verbose_name='【過去履歴1】タイム(馬)')
    time_diff_hh1 = models.FloatField(null=True, blank=True, db_column='TIME_DIFF_H_HISTORY1', help_text='着差_履歴1(馬)', verbose_name='【過去履歴1】着差(馬)')
    time_up_hh1 = models.FloatField(null=True, blank=True, db_column='TIME_UP_H_HISTORY1', help_text='上がりタイム_履歴1(馬)', verbose_name='【過去履歴1】上がりタイム(馬)')
    pace_1_hh1 = models.FloatField(null=True, blank=True, db_column='PACE_1_H_HISTORY1', help_text='前半ペース_履歴1(馬)', verbose_name='【過去履歴1】前半ペース(馬)')
    pace_2_hh1 = models.FloatField(null=True, blank=True, db_column='PACE_2_H_HISTORY1', help_text='後半ペース_履歴1(馬)', verbose_name='【過去履歴1】後半ペース(馬)')
    position_1_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1_H_HISTORY1', help_text='1/4順位_履歴1(馬)', verbose_name='【過去履歴1】1/4順位(馬)')
    position_2_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2_H_HISTORY1', help_text='2/4順位_履歴1(馬)', verbose_name='【過去履歴1】2/4順位(馬)')
    position_3_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3_H_HISTORY1', help_text='3/4順位_履歴1(馬)', verbose_name='【過去履歴1】3/4順位(馬)')
    position_4_hh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4_H_HISTORY1', help_text='4/4順位_履歴1(馬)', verbose_name='【過去履歴1】4/4順位(馬)')
    winner_hh1 = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER_H_HISTORY1', help_text='勝ち馬名_履歴1(馬)', verbose_name='【過去履歴1】勝ち馬名(馬)')
    prize_hh1 = models.IntegerField(null=True, blank=True, db_column='PRIZE_H_HISTORY1', help_text='賞金_履歴1(馬)', verbose_name='【過去履歴1】賞金(馬)')

    new_flg_hh1 = models.BooleanField(default=False, db_column='NEW_FLG_H_HISTORY1', help_text='新馬戦_履歴1(馬)', verbose_name='【過去履歴1】新馬戦(馬)')
    g1_flg_hh1 = models.BooleanField(default=False, db_column='G1_FLG_H_HISTORY1', help_text='G1戦_履歴1(馬)', verbose_name='【過去履歴1】G1戦(馬)')
    g2_flg_hh1 = models.BooleanField(default=False, db_column='G2_FLG_H_HISTORY1', help_text='G2戦_履歴1(馬)', verbose_name='【過去履歴1】G2戦(馬)')
    g3_flg_hh1 = models.BooleanField(default=False, db_column='G3_FLG_H_HISTORY1', help_text='G3戦_履歴1(馬)', verbose_name='【過去履歴1】G3戦(馬)')
    l_flg_hh1 = models.BooleanField(default=False, db_column='L_FLG_H_HISTORY1', help_text='リステッド_履歴1(馬)', verbose_name='【過去履歴1】リステッド(馬)')
    not_win_flg_hh1 = models.BooleanField(default=False, db_column='NOT_WIN_FLG_H_HISTORY1', help_text='未勝利戦_履歴1(馬)', verbose_name='【過去履歴1】未勝利戦(馬)')
    op_flg_hh1 = models.BooleanField(default=False, db_column='OP_FLG_H_HISTORY1', help_text='オープン戦_履歴1(馬)', verbose_name='【過去履歴1】オープン戦(馬)')
    win_1_flg_hh1 = models.BooleanField(default=False, db_column='WIN_1_FLG_H_HISTORY1', help_text='1勝馬戦_履歴1(馬)', verbose_name='【過去履歴1】1勝馬戦(馬)')
    win_2_flg_hh1 = models.BooleanField(default=False, db_column='WIN_2_FLG_H_HISTORY1', help_text='2勝馬戦_履歴1(馬)', verbose_name='【過去履歴1】2勝馬戦(馬)')
    win_3_flg_hh1 = models.BooleanField(default=False, db_column='WIN_3_FLG_H_HISTORY1', help_text='3勝馬戦_履歴1(馬)', verbose_name='【過去履歴1】3勝馬戦(馬)')

    # 過去馬レース２
    history_race_date_hh2 = models.DateField(null=True, blank=True, db_column='RACE_DATE_H_HISTORY2', help_text='過去レース日_履歴2(馬)', verbose_name='【過去履歴2】レース日(馬)')
    race_name_hh2 = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME_H_HISTORY2', help_text='レース名_履歴2(馬)', verbose_name='【過去履歴2】レース名(馬)')
    place_id_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID_H_HISTORY2', help_text='開催地ID_履歴2(馬)', verbose_name='【過去履歴2】開催地ID(馬)')
    place_name_hh2 = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME_H_HISTORY2', help_text='開催地名_履歴2(馬)', verbose_name='【過去履歴2】開催地名(馬)')
    track_condition_hh2 = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION_H_HISTORY2', help_text='馬場_履歴2(馬)', verbose_name='【過去履歴2】馬場(馬)')
    weather_hh2 = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER_H_HISTORY2', help_text='天気_履歴2(馬)', verbose_name='【過去履歴2】天気(馬)')
    count_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='COUNT_H_HISTORY2', help_text='頭数_履歴2(馬)', verbose_name='【過去履歴2】頭数(馬)')
    field_hh2 = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD_H_HISTORY2', help_text='場別_履歴2(馬)', verbose_name='【過去履歴2】場別(馬)')
    distance_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE_H_HISTORY2', help_text='距離(m)_履歴2(馬)', verbose_name='【過去履歴2】距離(m)(馬)')
    frame_number_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER_H_HISTORY2', help_text='枠番_履歴2(馬)', verbose_name='【過去履歴2】枠番(馬)')
    horse_number_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER_H_HISTORY2', help_text='馬番_履歴2(馬)', verbose_name='【過去履歴2】馬番(馬)')
    body_weight_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT_H_HISTORY2', help_text='馬体重_履歴2(馬)', verbose_name='【過去履歴2】馬体重(馬)')
    jockey_hh2 = models.CharField(max_length=20, null=True, blank=True, db_column='JOCKEY_H_HISTORY2', help_text='騎手名_履歴2(馬)', verbose_name='【過去履歴2】騎手名(馬)')
    odds_hh2 = models.FloatField(null=True, blank=True, db_column='ODDS_H_HISTORY2', help_text='オッズ_履歴2(馬)', verbose_name='【過去履歴2】単勝オッズ(馬)')
    popularity_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY_H_HISTORY2', help_text='人気_履歴2(馬)', verbose_name='【過去履歴2】人気(馬)')
    rank_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='RANK_H_HISTORY2', help_text='着順_履歴2(馬)', verbose_name='【過去履歴2】着順(馬)')
    time_hh2 = models.FloatField(null=True, blank=True, db_column='TIME_H_HISTORY2', help_text='タイム_履歴2(馬)', verbose_name='【過去履歴2】タイム(馬)')
    time_diff_hh2 = models.FloatField(null=True, blank=True, db_column='TIME_DIFF_H_HISTORY2', help_text='着差_履歴2(馬)', verbose_name='【過去履歴2】着差(馬)')
    time_up_hh2 = models.FloatField(null=True, blank=True, db_column='TIME_UP_H_HISTORY2', help_text='上がりタイム_履歴2(馬)', verbose_name='【過去履歴2】上がりタイム(馬)')
    pace_1_hh2 = models.FloatField(null=True, blank=True, db_column='PACE_1_H_HISTORY2', help_text='前半ペース_履歴2(馬)', verbose_name='【過去履歴2】前半ペース(馬)')
    pace_2_hh2 = models.FloatField(null=True, blank=True, db_column='PACE_2_H_HISTORY2', help_text='後半ペース_履歴2(馬)', verbose_name='【過去履歴2】後半ペース(馬)')
    position_1_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1_H_HISTORY2', help_text='1/4順位_履歴2(馬)', verbose_name='【過去履歴2】1/4順位(馬)')
    position_2_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2_H_HISTORY2', help_text='2/4順位_履歴2(馬)', verbose_name='【過去履歴2】2/4順位(馬)')
    position_3_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3_H_HISTORY2', help_text='3/4順位_履歴2(馬)', verbose_name='【過去履歴2】3/4順位(馬)')
    position_4_hh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4_H_HISTORY2', help_text='4/4順位_履歴2(馬)', verbose_name='【過去履歴2】4/4順位(馬)')
    winner_hh2 = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER_H_HISTORY2', help_text='勝ち馬名_履歴2(馬)', verbose_name='【過去履歴2】勝ち馬名(馬)')
    prize_hh2 = models.IntegerField(null=True, blank=True, db_column='PRIZE_H_HISTORY2', help_text='賞金_履歴2(馬)', verbose_name='【過去履歴2】賞金(馬)')

    new_flg_hh2 = models.BooleanField(default=False, db_column='NEW_FLG_H_HISTORY2', help_text='新馬戦_履歴2(馬)', verbose_name='【過去履歴2】新馬戦(馬)')
    g1_flg_hh2 = models.BooleanField(default=False, db_column='G1_FLG_H_HISTORY2', help_text='G1戦_履歴2(馬)', verbose_name='【過去履歴2】G1戦(馬)')
    g2_flg_hh2 = models.BooleanField(default=False, db_column='G2_FLG_H_HISTORY2', help_text='G2戦_履歴2(馬)', verbose_name='【過去履歴2】G2戦(馬)')
    g3_flg_hh2 = models.BooleanField(default=False, db_column='G3_FLG_H_HISTORY2', help_text='G3戦_履歴2(馬)', verbose_name='【過去履歴2】G3戦(馬)')
    l_flg_hh2 = models.BooleanField(default=False, db_column='L_FLG_H_HISTORY2', help_text='リステッド_履歴2(馬)', verbose_name='【過去履歴2】リステッド(馬)')
    not_win_flg_hh2 = models.BooleanField(default=False, db_column='NOT_WIN_FLG_H_HISTORY2', help_text='未勝利戦_履歴2(馬)', verbose_name='【過去履歴2】未勝利戦(馬)')
    op_flg_hh2 = models.BooleanField(default=False, db_column='OP_FLG_H_HISTORY2', help_text='オープン戦_履歴2(馬)', verbose_name='【過去履歴2】オープン戦(馬)')
    win_1_flg_hh2 = models.BooleanField(default=False, db_column='WIN_1_FLG_H_HISTORY2', help_text='1勝馬戦_履歴2(馬)', verbose_name='【過去履歴2】1勝馬戦(馬)')
    win_2_flg_hh2 = models.BooleanField(default=False, db_column='WIN_2_FLG_H_HISTORY2', help_text='2勝馬戦_履歴2(馬)', verbose_name='【過去履歴2】2勝馬戦(馬)')
    win_3_flg_hh2 = models.BooleanField(default=False, db_column='WIN_3_FLG_H_HISTORY2', help_text='3勝馬戦_履歴2(馬)', verbose_name='【過去履歴2】3勝馬戦(馬)')
        
    # 過去馬レース３
    history_race_date_hh3 = models.DateField(null=True, blank=True, db_column='RACE_DATE_H_HISTORY3', help_text='過去レース日_履歴3(馬)', verbose_name='【過去履歴3】レース日(馬)')
    race_name_hh3 = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME_H_HISTORY3', help_text='レース名_履歴3(馬)', verbose_name='【過去履歴3】レース名(馬)')
    place_id_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID_H_HISTORY3', help_text='開催地ID_履歴3(馬)', verbose_name='【過去履歴3】開催地ID(馬)')
    place_name_hh3 = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME_H_HISTORY3', help_text='開催地名_履歴3(馬)', verbose_name='【過去履歴3】開催地名(馬)')
    track_condition_hh3 = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION_H_HISTORY3', help_text='馬場_履歴3(馬)', verbose_name='【過去履歴3】馬場(馬)')
    weather_hh3 = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER_H_HISTORY3', help_text='天気_履歴3(馬)', verbose_name='【過去履歴3】天気(馬)')
    count_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='COUNT_H_HISTORY3', help_text='頭数_履歴3(馬)', verbose_name='【過去履歴3】頭数(馬)')
    field_hh3 = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD_H_HISTORY3', help_text='場別_履歴3(馬)', verbose_name='【過去履歴3】場別(馬)')
    distance_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE_H_HISTORY3', help_text='距離(m)_履歴3(馬)', verbose_name='【過去履歴3】距離(m)(馬)')
    frame_number_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER_H_HISTORY3', help_text='枠番_履歴3(馬)', verbose_name='【過去履歴3】枠番(馬)')
    horse_number_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER_H_HISTORY3', help_text='馬番_履歴3(馬)', verbose_name='【過去履歴3】馬番(馬)')
    body_weight_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT_H_HISTORY3', help_text='馬体重_履歴3(馬)', verbose_name='【過去履歴3】馬体重(馬)')
    jockey_hh3 = models.CharField(max_length=20, null=True, blank=True, db_column='JOCKEY_H_HISTORY3', help_text='騎手名_履歴3(馬)', verbose_name='【過去履歴3】騎手名(馬)')
    odds_hh3 = models.FloatField(null=True, blank=True, db_column='ODDS_H_HISTORY3', help_text='オッズ_履歴3(馬)', verbose_name='【過去履歴3】単勝オッズ(馬)')
    popularity_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY_H_HISTORY3', help_text='人気_履歴3(馬)', verbose_name='【過去履歴3】人気(馬)')
    rank_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='RANK_H_HISTORY3', help_text='着順_履歴3(馬)', verbose_name='【過去履歴3】着順(馬)')
    time_hh3 = models.FloatField(null=True, blank=True, db_column='TIME_H_HISTORY3', help_text='タイム_履歴3(馬)', verbose_name='【過去履歴3】タイム(馬)')
    time_diff_hh3 = models.FloatField(null=True, blank=True, db_column='TIME_DIFF_H_HISTORY3', help_text='着差_履歴3(馬)', verbose_name='【過去履歴3】着差(馬)')
    time_up_hh3 = models.FloatField(null=True, blank=True, db_column='TIME_UP_H_HISTORY3', help_text='上がりタイム_履歴3(馬)', verbose_name='【過去履歴3】上がりタイム(馬)')
    pace_1_hh3 = models.FloatField(null=True, blank=True, db_column='PACE_1_H_HISTORY3', help_text='前半ペース_履歴3(馬)', verbose_name='【過去履歴3】前半ペース(馬)')
    pace_2_hh3 = models.FloatField(null=True, blank=True, db_column='PACE_2_H_HISTORY3', help_text='後半ペース_履歴3(馬)', verbose_name='【過去履歴3】後半ペース(馬)')
    position_1_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1_H_HISTORY3', help_text='1/4順位_履歴3(馬)', verbose_name='【過去履歴3】1/4順位(馬)')
    position_2_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2_H_HISTORY3', help_text='2/4順位_履歴3(馬)', verbose_name='【過去履歴3】2/4順位(馬)')
    position_3_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3_H_HISTORY3', help_text='3/4順位_履歴3(馬)', verbose_name='【過去履歴3】3/4順位(馬)')
    position_4_hh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4_H_HISTORY3', help_text='4/4順位_履歴3(馬)', verbose_name='【過去履歴3】4/4順位(馬)')
    winner_hh3 = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER_H_HISTORY3', help_text='勝ち馬名_履歴3(馬)', verbose_name='【過去履歴3】勝ち馬名(馬)')
    prize_hh3 = models.IntegerField(null=True, blank=True, db_column='PRIZE_H_HISTORY3', help_text='賞金_履歴3(馬)', verbose_name='【過去履歴3】賞金(馬)')

    new_flg_hh3 = models.BooleanField(default=False, db_column='NEW_FLG_H_HISTORY3', help_text='新馬戦_履歴3(馬)', verbose_name='【過去履歴3】新馬戦(馬)')
    g1_flg_hh3 = models.BooleanField(default=False, db_column='G1_FLG_H_HISTORY3', help_text='G1戦_履歴3(馬)', verbose_name='【過去履歴3】G1戦(馬)')
    g2_flg_hh3 = models.BooleanField(default=False, db_column='G2_FLG_H_HISTORY3', help_text='G2戦_履歴3(馬)', verbose_name='【過去履歴3】G2戦(馬)')
    g3_flg_hh3 = models.BooleanField(default=False, db_column='G3_FLG_H_HISTORY3', help_text='G3戦_履歴3(馬)', verbose_name='【過去履歴3】G3戦(馬)')
    l_flg_hh3 = models.BooleanField(default=False, db_column='L_FLG_H_HISTORY3', help_text='リステッド_履歴3(馬)', verbose_name='【過去履歴3】リステッド(馬)')
    not_win_flg_hh3 = models.BooleanField(default=False, db_column='NOT_WIN_FLG_H_HISTORY3', help_text='未勝利戦_履歴3(馬)', verbose_name='【過去履歴3】未勝利戦(馬)')
    op_flg_hh3 = models.BooleanField(default=False, db_column='OP_FLG_H_HISTORY3', help_text='オープン戦_履歴3(馬)', verbose_name='【過去履歴3】オープン戦(馬)')
    win_1_flg_hh3 = models.BooleanField(default=False, db_column='WIN_1_FLG_H_HISTORY3', help_text='1勝馬戦_履歴3(馬)', verbose_name='【過去履歴3】1勝馬戦(馬)')
    win_2_flg_hh3 = models.BooleanField(default=False, db_column='WIN_2_FLG_H_HISTORY3', help_text='2勝馬戦_履歴3(馬)', verbose_name='【過去履歴3】2勝馬戦(馬)')
    win_3_flg_hh3 = models.BooleanField(default=False, db_column='WIN_3_FLG_H_HISTORY3', help_text='3勝馬戦_履歴3(馬)', verbose_name='【過去履歴3】3勝馬戦(馬)')
        
    # 過去騎手レース１
    history_race_date_jh1 = models.DateField(null=True, blank=True, db_column='RACE_DATE_J_HISTORY1', help_text='レース日_履歴1(騎手)', verbose_name='【過去履歴1】レース日(騎手)')
    history_race_no_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='RACE_NO_J_HISTORY1', help_text='レース番号_履歴1(騎手)', verbose_name='【過去履歴1】レース番号(騎手)')
    race_name_jh1 = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME_J_HISTORY1', help_text='レース名_履歴1(騎手)', verbose_name='【過去履歴1】レース名(騎手)')
    track_condition_jh1 = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION_J_HISTORY1', help_text='馬場_履歴1(騎手)', verbose_name='【過去履歴1】馬場(騎手)')
    weather_jh1 = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER_J_HISTORY1', help_text='天気_履歴1(騎手)', verbose_name='【過去履歴1】天気(騎手)')
    place_id_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID_J_HISTORY1', help_text='開催地ID_履歴1(騎手)', verbose_name='【過去履歴1】開催地ID(騎手)')
    place_name_jh1 = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME_J_HISTORY1', help_text='開催地名_履歴1(騎手)', verbose_name='【過去履歴1】開催地名(騎手)')
    count_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='COUNT_J_HISTORY1', help_text='頭数_履歴1(騎手)', verbose_name='【過去履歴1】頭数(騎手)')
    field_jh1 = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD_J_HISTORY1', help_text='場別_履歴1(騎手)', verbose_name='【過去履歴1】場別(騎手)')
    distance_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE_J_HISTORY1', help_text='距離(m)_履歴1(騎手)', verbose_name='【過去履歴1】距離(m)(騎手)')

    body_weight_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT_J_HISTORY1', help_text='馬体重_履歴1(騎手)', verbose_name='【過去履歴1】馬体重(騎手)')
    weight_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='WEIGHT_J_HISTORY1', help_text='斤量_履歴1(騎手)', verbose_name='【過去履歴1】斤量(騎手)')
    frame_number_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER_J_HISTORY1', help_text='枠番_履歴1(騎手)', verbose_name='【過去履歴1】枠番(騎手)')
    horse_number_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER_J_HISTORY1', help_text='馬番_履歴1(騎手)', verbose_name='【過去履歴1】馬番(騎手)')
    horse_jh1 = models.CharField(max_length=20, null=True, blank=True, db_column='HORSE_J_HISTORY1', help_text='馬名_履歴1(騎手)', verbose_name='【過去履歴1】馬名(騎手)')

    rank_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='RANK_J_HISTORY1', help_text='着順_履歴1(騎手)', verbose_name='【過去履歴1】着順(騎手)')
    time_jh1 = models.FloatField(null=True, blank=True, db_column='TIME_J_HISTORY1', help_text='タイム_履歴1(騎手)', verbose_name='【過去履歴1】タイム(騎手)')
    time_diff_jh1 = models.FloatField(null=True, blank=True, db_column='TIME_DIFF_J_HISTORY1', help_text='着差_履歴1(騎手)', verbose_name='【過去履歴1】着差(騎手)')
    time_up_jh1 = models.FloatField(null=True, blank=True, db_column='TIME_UP_J_HISTORY1', help_text='上がりタイム_履歴1(騎手)', verbose_name='【過去履歴1】上がりタイム(騎手)')

    pace_1_jh1 = models.FloatField(null=True, blank=True, db_column='PACE_1_J_HISTORY1', help_text='前半ペース_履歴1(騎手)', verbose_name='【過去履歴1】前半ペース(騎手)')
    pace_2_jh1 = models.FloatField(null=True, blank=True, db_column='PACE_2_J_HISTORY1', help_text='後半ペース_履歴1(騎手)', verbose_name='【過去履歴1】後半ペース(騎手)')

    position_1_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1_J_HISTORY1', help_text='1/4順位_履歴1(騎手)', verbose_name='【過去履歴1】1/4順位(騎手)')
    position_2_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2_J_HISTORY1', help_text='2/4順位_履歴1(騎手)', verbose_name='【過去履歴1】2/4順位(騎手)')
    position_3_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3_J_HISTORY1', help_text='3/4順位_履歴1(騎手)', verbose_name='【過去履歴1】3/4順位(騎手)')
    position_4_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4_J_HISTORY1', help_text='4/4順位_履歴1(騎手)', verbose_name='【過去履歴1】4/4順位(騎手)')

    odds_jh1 = models.FloatField(null=True, blank=True, db_column='ODDS_J_HISTORY1', help_text='オッズ_履歴1(騎手)', verbose_name='【過去履歴1】単勝オッズ(騎手)')
    popularity_jh1 = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY_J_HISTORY1', help_text='人気_履歴1(騎手)', verbose_name='【過去履歴1】人気(騎手)')

    winner_jh1 = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER_J_HISTORY1', help_text='勝ち馬名_履歴1(騎手)', verbose_name='【過去履歴1】勝ち馬名(騎手)')
    prize_jh1 = models.IntegerField(null=True, blank=True, db_column='PRIZE_J_HISTORY1', help_text='賞金_履歴1(騎手)', verbose_name='【過去履歴1】賞金(騎手)')

    weight_4kg_cut_flg_jh1 = models.BooleanField(default=False, db_column='WEIGHT_4KG_CUT_FLG_J_HISTORY1', help_text='ハンデ4KG_履歴1(騎手)', verbose_name='【過去履歴1】ハンデ4KG(騎手)')
    weight_3kg_cut_flg_jh1 = models.BooleanField(default=False, db_column='WEIGHT_3KG_CUT_FLG_J_HISTORY1', help_text='ハンデ3KG_履歴1(騎手)', verbose_name='【過去履歴1】ハンデ3KG(騎手)')
    weight_2kg_cut_flg_jh1 = models.BooleanField(default=False, db_column='WEIGHT_2KG_CUT_FLG_J_HISTORY1', help_text='ハンデ2KG_履歴1(騎手)', verbose_name='【過去履歴1】ハンデ2KG(騎手)')
    weight_1kg_cut_flg_jh1 = models.BooleanField(default=False, db_column='WEIGHT_1KG_CUT_FLG_J_HISTORY1', help_text='ハンデ1KG_履歴1(騎手)', verbose_name='【過去履歴1】ハンデ1KG(騎手)')
    women_weight_2kg_cut_flg_jh1 = models.BooleanField(default=False, db_column='WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY1', help_text='女性ハンデ2KG_履歴1(騎手)', verbose_name='【過去履歴1】女性ハンデ2KG(騎手)')

    new_flg_jh1 = models.BooleanField(default=False, db_column='NEW_FLG_J_HISTORY1', help_text='新馬戦_履歴1(騎手)', verbose_name='【過去履歴1】新馬戦(騎手)')
    g1_flg_jh1 = models.BooleanField(default=False, db_column='G1_FLG_J_HISTORY1', help_text='G1戦_履歴1(騎手)', verbose_name='【過去履歴1】G1戦(騎手)')
    g2_flg_jh1 = models.BooleanField(default=False, db_column='G2_FLG_J_HISTORY1', help_text='G2戦_履歴1(騎手)', verbose_name='【過去履歴1】G2戦(騎手)')
    g3_flg_jh1 = models.BooleanField(default=False, db_column='G3_FLG_J_HISTORY1', help_text='G3戦_履歴1(騎手)', verbose_name='【過去履歴1】G3戦(騎手)')
    l_flg_jh1 = models.BooleanField(default=False, db_column='L_FLG_J_HISTORY1', help_text='リステッド戦_履歴1(騎手)', verbose_name='【過去履歴1】リステッド戦(騎手)')
    not_win_flg_jh1 = models.BooleanField(default=False, db_column='NOT_WIN_FLG_J_HISTORY1', help_text='未勝利戦_履歴1(騎手)', verbose_name='【過去履歴1】未勝利戦(騎手)')
    op_flg_jh1 = models.BooleanField(default=False, db_column='OP_FLG_J_HISTORY1', help_text='オープン戦_履歴1(騎手)', verbose_name='【過去履歴1】オープン戦(騎手)')
    win_1_flg_jh1 = models.BooleanField(default=False, db_column='WIN_1_FLG_J_HISTORY1', help_text='1勝馬戦_履歴1(騎手)', verbose_name='【過去履歴1】1勝馬戦(騎手)')
    win_2_flg_jh1 = models.BooleanField(default=False, db_column='WIN_2_FLG_J_HISTORY1', help_text='2勝馬戦_履歴1(騎手)', verbose_name='【過去履歴1】2勝馬戦(騎手)')
    win_3_flg_jh1 = models.BooleanField(default=False, db_column='WIN_3_FLG_J_HISTORY1', help_text='3勝馬戦_履歴1(騎手)', verbose_name='【過去履歴1】3勝馬戦(騎手)')
        
    # 過去騎手レース２
    history_race_date_jh2 = models.DateField(null=True, blank=True, db_column='RACE_DATE_J_HISTORY2', help_text='レース日_履歴2(騎手)', verbose_name='【過去履歴2】レース日(騎手)')
    history_race_no_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='RACE_NO_J_HISTORY2', help_text='レース番号_履歴2(騎手)', verbose_name='【過去履歴2】レース番号(騎手)')
    race_name_jh2 = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME_J_HISTORY2', help_text='レース名_履歴2(騎手)', verbose_name='【過去履歴2】レース名(騎手)')
    track_condition_jh2 = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION_J_HISTORY2', help_text='馬場_履歴2(騎手)', verbose_name='【過去履歴2】馬場(騎手)')
    weather_jh2 = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER_J_HISTORY2', help_text='天気_履歴2(騎手)', verbose_name='【過去履歴2】天気(騎手)')
    place_id_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID_J_HISTORY2', help_text='開催地ID_履歴2(騎手)', verbose_name='【過去履歴2】開催地ID(騎手)')
    place_name_jh2 = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME_J_HISTORY2', help_text='開催地名_履歴2(騎手)', verbose_name='【過去履歴2】開催地名(騎手)')
    count_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='COUNT_J_HISTORY2', help_text='頭数_履歴2(騎手)', verbose_name='【過去履歴2】頭数(騎手)')
    field_jh2 = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD_J_HISTORY2', help_text='場別_履歴2(騎手)', verbose_name='【過去履歴2】場別(騎手)')
    distance_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE_J_HISTORY2', help_text='距離(m)_履歴2(騎手)', verbose_name='【過去履歴2】距離(m)(騎手)')

    body_weight_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT_J_HISTORY2', help_text='馬体重_履歴2(騎手)', verbose_name='【過去履歴2】馬体重(騎手)')
    weight_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='WEIGHT_J_HISTORY2', help_text='斤量_履歴2(騎手)', verbose_name='【過去履歴2】斤量(騎手)')
    frame_number_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER_J_HISTORY2', help_text='枠番_履歴2(騎手)', verbose_name='【過去履歴2】枠番(騎手)')
    horse_number_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER_J_HISTORY2', help_text='馬番_履歴2(騎手)', verbose_name='【過去履歴2】馬番(騎手)')
    horse_jh2 = models.CharField(max_length=20, null=True, blank=True, db_column='HORSE_J_HISTORY2', help_text='馬名_履歴2(騎手)', verbose_name='【過去履歴2】馬名(騎手)')

    rank_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='RANK_J_HISTORY2', help_text='着順_履歴2(騎手)', verbose_name='【過去履歴2】着順(騎手)')
    time_jh2 = models.FloatField(null=True, blank=True, db_column='TIME_J_HISTORY2', help_text='タイム_履歴2(騎手)', verbose_name='【過去履歴2】タイム(騎手)')
    time_diff_jh2 = models.FloatField(null=True, blank=True, db_column='TIME_DIFF_J_HISTORY2', help_text='着差_履歴2(騎手)', verbose_name='【過去履歴2】着差(騎手)')
    time_up_jh2 = models.FloatField(null=True, blank=True, db_column='TIME_UP_J_HISTORY2', help_text='上がりタイム_履歴2(騎手)', verbose_name='【過去履歴2】上がりタイム(騎手)')

    pace_1_jh2 = models.FloatField(null=True, blank=True, db_column='PACE_1_J_HISTORY2', help_text='前半ペース_履歴2(騎手)', verbose_name='【過去履歴2】前半ペース(騎手)')
    pace_2_jh2 = models.FloatField(null=True, blank=True, db_column='PACE_2_J_HISTORY2', help_text='後半ペース_履歴2(騎手)', verbose_name='【過去履歴2】後半ペース(騎手)')

    position_1_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1_J_HISTORY2', help_text='1/4順位_履歴2(騎手)', verbose_name='【過去履歴2】1/4順位(騎手)')
    position_2_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2_J_HISTORY2', help_text='2/4順位_履歴2(騎手)', verbose_name='【過去履歴2】2/4順位(騎手)')
    position_3_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3_J_HISTORY2', help_text='3/4順位_履歴2(騎手)', verbose_name='【過去履歴2】3/4順位(騎手)')
    position_4_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4_J_HISTORY2', help_text='4/4順位_履歴2(騎手)', verbose_name='【過去履歴2】4/4順位(騎手)')

    odds_jh2 = models.FloatField(null=True, blank=True, db_column='ODDS_J_HISTORY2', help_text='オッズ_履歴2(騎手)', verbose_name='【過去履歴2】単勝オッズ(騎手)')
    popularity_jh2 = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY_J_HISTORY2', help_text='人気_履歴2(騎手)', verbose_name='【過去履歴2】人気(騎手)')

    winner_jh2 = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER_J_HISTORY2', help_text='勝ち馬名_履歴2(騎手)', verbose_name='【過去履歴2】勝ち馬名(騎手)')
    prize_jh2 = models.IntegerField(null=True, blank=True, db_column='PRIZE_J_HISTORY2', help_text='賞金_履歴2(騎手)', verbose_name='【過去履歴2】賞金(騎手)')

    weight_4kg_cut_flg_jh2 = models.BooleanField(default=False, db_column='WEIGHT_4KG_CUT_FLG_J_HISTORY2', help_text='ハンデ4KG_履歴2(騎手)', verbose_name='【過去履歴2】ハンデ4KG(騎手)')
    weight_3kg_cut_flg_jh2 = models.BooleanField(default=False, db_column='WEIGHT_3KG_CUT_FLG_J_HISTORY2', help_text='ハンデ3KG_履歴2(騎手)', verbose_name='【過去履歴2】ハンデ3KG(騎手)')
    weight_2kg_cut_flg_jh2 = models.BooleanField(default=False, db_column='WEIGHT_2KG_CUT_FLG_J_HISTORY2', help_text='ハンデ2KG_履歴2(騎手)', verbose_name='【過去履歴2】ハンデ2KG(騎手)')
    weight_1kg_cut_flg_jh2 = models.BooleanField(default=False, db_column='WEIGHT_1KG_CUT_FLG_J_HISTORY2', help_text='ハンデ1KG_履歴2(騎手)', verbose_name='【過去履歴2】ハンデ1KG(騎手)')
    women_weight_2kg_cut_flg_jh2 = models.BooleanField(default=False, db_column='WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY2', help_text='女性ハンデ2KG_履歴2(騎手)', verbose_name='【過去履歴2】女性ハンデ2KG(騎手)')

    new_flg_jh2 = models.BooleanField(default=False, db_column='NEW_FLG_J_HISTORY2', help_text='新馬戦_履歴2(騎手)', verbose_name='【過去履歴2】新馬戦(騎手)')
    g1_flg_jh2 = models.BooleanField(default=False, db_column='G1_FLG_J_HISTORY2', help_text='G1戦_履歴2(騎手)', verbose_name='【過去履歴2】G1戦(騎手)')
    g2_flg_jh2 = models.BooleanField(default=False, db_column='G2_FLG_J_HISTORY2', help_text='G2戦_履歴2(騎手)', verbose_name='【過去履歴2】G2戦(騎手)')
    g3_flg_jh2 = models.BooleanField(default=False, db_column='G3_FLG_J_HISTORY2', help_text='G3戦_履歴2(騎手)', verbose_name='【過去履歴2】G3戦(騎手)')
    l_flg_jh2 = models.BooleanField(default=False, db_column='L_FLG_J_HISTORY2', help_text='リステッド戦_履歴2(騎手)', verbose_name='【過去履歴2】リステッド戦(騎手)')
    not_win_flg_jh2 = models.BooleanField(default=False, db_column='NOT_WIN_FLG_J_HISTORY2', help_text='未勝利戦_履歴2(騎手)', verbose_name='【過去履歴2】未勝利戦(騎手)')
    op_flg_jh2 = models.BooleanField(default=False, db_column='OP_FLG_J_HISTORY2', help_text='オープン戦_履歴2(騎手)', verbose_name='【過去履歴2】オープン戦(騎手)')
    win_1_flg_jh2 = models.BooleanField(default=False, db_column='WIN_1_FLG_J_HISTORY2', help_text='1勝馬戦_履歴2(騎手)', verbose_name='【過去履歴2】1勝馬戦(騎手)')
    win_2_flg_jh2 = models.BooleanField(default=False, db_column='WIN_2_FLG_J_HISTORY2', help_text='2勝馬戦_履歴2(騎手)', verbose_name='【過去履歴2】2勝馬戦(騎手)')
    win_3_flg_jh2 = models.BooleanField(default=False, db_column='WIN_3_FLG_J_HISTORY2', help_text='3勝馬戦_履歴2(騎手)', verbose_name='【過去履歴2】3勝馬戦(騎手)')
        
    # 過去騎手レース３
    history_race_date_jh3 = models.DateField(null=True, blank=True, db_column='RACE_DATE_J_HISTORY3', help_text='レース日_履歴3(騎手)', verbose_name='【過去履歴3】レース日(騎手)')
    history_race_no_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='RACE_NO_J_HISTORY3', help_text='レース番号_履歴3(騎手)', verbose_name='【過去履歴3】レース番号(騎手)')
    race_name_jh3 = models.CharField(max_length=50, null=True, blank=True, db_column='RACE_NAME_J_HISTORY3', help_text='レース名_履歴3(騎手)', verbose_name='【過去履歴3】レース名(騎手)')
    track_condition_jh3 = models.CharField(max_length=5, null=True, blank=True, db_column='TRACK_CONDITION_J_HISTORY3', help_text='馬場_履歴3(騎手)', verbose_name='【過去履歴3】馬場(騎手)')
    weather_jh3 = models.CharField(max_length=5, null=True, blank=True, db_column='WEATHER_J_HISTORY3', help_text='天気_履歴3(騎手)', verbose_name='【過去履歴3】天気(騎手)')
    place_id_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='PLACE_ID_J_HISTORY3', help_text='開催地ID_履歴3(騎手)', verbose_name='【過去履歴3】開催地ID(騎手)')
    place_name_jh3 = models.CharField(max_length=10, null=True, blank=True, db_column='PLACE_NAME_J_HISTORY3', help_text='開催地名_履歴3(騎手)', verbose_name='【過去履歴3】開催地名(騎手)')
    count_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='COUNT_J_HISTORY3', help_text='頭数_履歴3(騎手)', verbose_name='【過去履歴3】頭数(騎手)')
    field_jh3 = models.CharField(max_length=5, null=True, blank=True, db_column='FIELD_J_HISTORY3', help_text='場別_履歴3(騎手)', verbose_name='【過去履歴3】場別(騎手)')
    distance_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='DISTANCE_J_HISTORY3', help_text='距離(m)_履歴3(騎手)', verbose_name='【過去履歴3】距離(m)(騎手)')

    body_weight_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='BODY_WEIGHT_J_HISTORY3', help_text='馬体重_履歴3(騎手)', verbose_name='【過去履歴3】馬体重(騎手)')
    weight_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='WEIGHT_J_HISTORY3', help_text='斤量_履歴3(騎手)', verbose_name='【過去履歴3】斤量(騎手)')
    frame_number_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='FRAME_NUMBER_J_HISTORY3', help_text='枠番_履歴3(騎手)', verbose_name='【過去履歴3】枠番(騎手)')
    horse_number_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='HORSE_NUMBER_J_HISTORY3', help_text='馬番_履歴3(騎手)', verbose_name='【過去履歴3】馬番(騎手)')
    horse_jh3 = models.CharField(max_length=20, null=True, blank=True, db_column='HORSE_J_HISTORY3', help_text='馬名_履歴3(騎手)', verbose_name='【過去履歴3】馬名(騎手)')

    rank_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='RANK_J_HISTORY3', help_text='着順_履歴3(騎手)', verbose_name='【過去履歴3】着順(騎手)')
    time_jh3 = models.FloatField(null=True, blank=True, db_column='TIME_J_HISTORY3', help_text='タイム_履歴3(騎手)', verbose_name='【過去履歴3】タイム(騎手)')
    time_diff_jh3 = models.FloatField(null=True, blank=True, db_column='TIME_DIFF_J_HISTORY3', help_text='着差_履歴3(騎手)', verbose_name='【過去履歴3】着差(騎手)')
    time_up_jh3 = models.FloatField(null=True, blank=True, db_column='TIME_UP_J_HISTORY3', help_text='上がりタイム_履歴3(騎手)', verbose_name='【過去履歴3】上がりタイム(騎手)')

    pace_1_jh3 = models.FloatField(null=True, blank=True, db_column='PACE_1_J_HISTORY3', help_text='前半ペース_履歴3(騎手)', verbose_name='【過去履歴3】前半ペース(騎手)')
    pace_2_jh3 = models.FloatField(null=True, blank=True, db_column='PACE_2_J_HISTORY3', help_text='後半ペース_履歴3(騎手)', verbose_name='【過去履歴3】後半ペース(騎手)')

    position_1_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_1_J_HISTORY3', help_text='1/4順位_履歴3(騎手)', verbose_name='【過去履歴3】1/4順位(騎手)')
    position_2_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_2_J_HISTORY3', help_text='2/4順位_履歴3(騎手)', verbose_name='【過去履歴3】2/4順位(騎手)')
    position_3_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_3_J_HISTORY3', help_text='3/4順位_履歴3(騎手)', verbose_name='【過去履歴3】3/4順位(騎手)')
    position_4_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='POSITION_4_J_HISTORY3', help_text='4/4順位_履歴3(騎手)', verbose_name='【過去履歴3】4/4順位(騎手)')

    odds_jh3 = models.FloatField(null=True, blank=True, db_column='ODDS_J_HISTORY3', help_text='オッズ_履歴3(騎手)', verbose_name='【過去履歴3】単勝オッズ(騎手)')
    popularity_jh3 = models.SmallIntegerField(null=True, blank=True, db_column='POPULARITY_J_HISTORY3', help_text='人気_履歴3(騎手)', verbose_name='【過去履歴3】人気(騎手)')

    winner_jh3 = models.CharField(max_length=20, null=True, blank=True, db_column='WINNER_J_HISTORY3', help_text='勝ち馬名_履歴3(騎手)', verbose_name='【過去履歴3】勝ち馬名(騎手)')
    prize_jh3 = models.IntegerField(null=True, blank=True, db_column='PRIZE_J_HISTORY3', help_text='賞金_履歴3(騎手)', verbose_name='【過去履歴3】賞金(騎手)')

    weight_4kg_cut_flg_jh3 = models.BooleanField(default=False, db_column='WEIGHT_4KG_CUT_FLG_J_HISTORY3', help_text='ハンデ4KG_履歴3(騎手)', verbose_name='【過去履歴3】ハンデ4KG(騎手)')
    weight_3kg_cut_flg_jh3 = models.BooleanField(default=False, db_column='WEIGHT_3KG_CUT_FLG_J_HISTORY3', help_text='ハンデ3KG_履歴3(騎手)', verbose_name='【過去履歴3】ハンデ3KG(騎手)')
    weight_2kg_cut_flg_jh3 = models.BooleanField(default=False, db_column='WEIGHT_2KG_CUT_FLG_J_HISTORY3', help_text='ハンデ2KG_履歴3(騎手)', verbose_name='【過去履歴3】ハンデ2KG(騎手)')
    weight_1kg_cut_flg_jh3 = models.BooleanField(default=False, db_column='WEIGHT_1KG_CUT_FLG_J_HISTORY3', help_text='ハンデ1KG_履歴3(騎手)', verbose_name='【過去履歴3】ハンデ1KG(騎手)')
    women_weight_2kg_cut_flg_jh3 = models.BooleanField(default=False, db_column='WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY3', help_text='女性ハンデ2KG_履歴3(騎手)', verbose_name='【過去履歴3】女性ハンデ2KG(騎手)')

    new_flg_jh3 = models.BooleanField(default=False, db_column='NEW_FLG_J_HISTORY3', help_text='新馬戦_履歴3(騎手)', verbose_name='【過去履歴3】新馬戦(騎手)')
    g1_flg_jh3 = models.BooleanField(default=False, db_column='G1_FLG_J_HISTORY3', help_text='G1戦_履歴3(騎手)', verbose_name='【過去履歴3】G1戦(騎手)')
    g2_flg_jh3 = models.BooleanField(default=False, db_column='G2_FLG_J_HISTORY3', help_text='G2戦_履歴3(騎手)', verbose_name='【過去履歴3】G2戦(騎手)')
    g3_flg_jh3 = models.BooleanField(default=False, db_column='G3_FLG_J_HISTORY3', help_text='G3戦_履歴3(騎手)', verbose_name='【過去履歴3】G3戦(騎手)')
    l_flg_jh3 = models.BooleanField(default=False, db_column='L_FLG_J_HISTORY3', help_text='リステッド戦_履歴3(騎手)', verbose_name='【過去履歴3】リステッド戦(騎手)')
    not_win_flg_jh3 = models.BooleanField(default=False, db_column='NOT_WIN_FLG_J_HISTORY3', help_text='未勝利戦_履歴3(騎手)', verbose_name='【過去履歴3】未勝利戦(騎手)')
    op_flg_jh3 = models.BooleanField(default=False, db_column='OP_FLG_J_HISTORY3', help_text='オープン戦_履歴3(騎手)', verbose_name='【過去履歴3】オープン戦(騎手)')
    win_1_flg_jh3 = models.BooleanField(default=False, db_column='WIN_1_FLG_J_HISTORY3', help_text='1勝馬戦_履歴3(騎手)', verbose_name='【過去履歴3】1勝馬戦(騎手)')
    win_2_flg_jh3 = models.BooleanField(default=False, db_column='WIN_2_FLG_J_HISTORY3', help_text='2勝馬戦_履歴3(騎手)', verbose_name='【過去履歴3】2勝馬戦(騎手)')
    win_3_flg_jh3 = models.BooleanField(default=False, db_column='WIN_3_FLG_J_HISTORY3', help_text='3勝馬戦_履歴3(騎手)', verbose_name='【過去履歴3】3勝馬戦(騎手)')
    
    # レース結果
    rank = models.SmallIntegerField(null=True, blank=True, db_column='RANK', help_text='順位', verbose_name='【結果】順位')
    race_time = models.FloatField(null=True, blank=True, db_column='RACE_TIME', help_text='レースタイム', verbose_name='【結果】レースタイム')
    corner_order = models.CharField(max_length=20, null=True, blank=True, db_column='CORNER_ORDER', help_text='コーナー順', verbose_name='【結果】コーナー順')
    positions = models.CharField(max_length=10, null=True, blank=True, db_column='POSITIONS', help_text='着順', verbose_name='【結果】着順')
    positions_tie = models.CharField(max_length=10, null=True, blank=True, db_column='POSITIONS_TIE', help_text='着順_同着', verbose_name='【結果】着順_同着')

    pay1 = models.IntegerField(null=True, blank=True, db_column='PAY1', help_text='単勝払戻', verbose_name='【結果】単勝払戻')
    pay1_tie = models.IntegerField(null=True, blank=True, db_column='PAY1_TIE', help_text='単勝同着払戻', verbose_name='【結果】単勝同着払戻')

    pay123_1 = models.IntegerField(null=True, blank=True, db_column='PAY123_1', help_text='3連単_1番目', verbose_name='【結果】3連単_1番目')
    pay123_2 = models.IntegerField(null=True, blank=True, db_column='PAY123_2', help_text='3連単_2番目', verbose_name='【結果】3連単_2番目')
    pay123_3 = models.IntegerField(null=True, blank=True, db_column='PAY123_3', help_text='3連単_3番目', verbose_name='【結果】3連単_3番目')
    pay123_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_TIE', help_text='3連単_同着', verbose_name='【結果】3連単_同着')

    pay123_12_1 = models.IntegerField(null=True, blank=True, db_column='PAY123_12_1', help_text='ワイド_1番目', verbose_name='【結果】ワイド_1番目')
    pay123_12_2 = models.IntegerField(null=True, blank=True, db_column='PAY123_12_2', help_text='ワイド_2番目', verbose_name='【結果】ワイド_2番目')
    pay123_12_3 = models.IntegerField(null=True, blank=True, db_column='PAY123_12_3', help_text='ワイド_3番目', verbose_name='【結果】ワイド_3番目')
    pay123_12_4_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_12_4_TIE', help_text='ワイド_4番目_同着', verbose_name='【結果】ワイド_4番目_同着')
    pay123_12_5_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_12_5_TIE', help_text='ワイド_5番目_同着', verbose_name='【結果】ワイド_5番目_同着')

    pay12_21 = models.IntegerField(null=True, blank=True, db_column='PAY12_21', help_text='2連複', verbose_name='【結果】2連複')
    pay12_21_tie = models.IntegerField(null=True, blank=True, db_column='PAY12_21_TIE', help_text='2連複_同着', verbose_name='【結果】2連複_同着')
    pay12_12 = models.IntegerField(null=True, blank=True, db_column='PAY12_12', help_text='2連単', verbose_name='【結果】2連単')
    pay12_12_tie = models.IntegerField(null=True, blank=True, db_column='PAY12_12_TIE', help_text='2連単_同着', verbose_name='【結果】2連単_同着')

    pay123_321 = models.IntegerField(null=True, blank=True, db_column='PAY123_321', help_text='3連複', verbose_name='【結果】3連複')
    pay123_321_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_321_TIE', help_text='3連複_同着', verbose_name='【結果】3連複_同着')
    pay123_123 = models.IntegerField(null=True, blank=True, db_column='PAY123_123', help_text='3連単', verbose_name='【結果】3連単')
    pay123_123_tie = models.IntegerField(null=True, blank=True, db_column='PAY123_123_TIE', help_text='3連単_同着', verbose_name='【結果】3連単_同着')

    def __str__(self):
        return f"{self.race_id} - {self.horse} ({self.horse_number})"

# Viewクラス
class CompareView(models.Model):
    class Meta:
        managed = False
        db_table = 'v_compare_base_result'
    race_id = models.CharField(max_length=12, db_comment="レースID", help_text="レースID") 
    horse_number = models.CharField(max_length=5, db_comment="馬番", help_text="馬番")
    race_date = models.DateField(db_comment="レース日付", help_text="レース日付") 

class CreateRaceIDsView(models.Model):
    class Meta:
        managed = False
        db_table = 'v_create_race_ids'
    
    race_id = models.CharField(max_length=12, db_comment="レースID", help_text="レースID")
    url = models.CharField(db_comment="URL", help_text="URL")

class WeekEndView(models.Model):
    class Meta:
        managed = False
        db_table = 'v_weekend'
    
    race_date = models.DateField(db_comment="レース日付", help_text="レース日付") 
    race_date_null = models.DateField(db_comment="レース日付_NULL", help_text="レース日付_NULL") 
    race_id = models.CharField(db_comment="レースID_NULL", help_text="レースID_NULL") 

class CompareBaseHorseView(models.Model):
    class Meta:
        managed = False
        db_table = 'v_compare_base_horse'

    race_date = models.DateField(db_comment="レース日付", help_text="レース日付") 
    horse_name = models.CharField(db_comment="馬名", help_text="馬名")
    horse_url = models.CharField(db_comment="馬URL", help_text="馬URL")

class CompareBaseJockeyView(models.Model):
    class Meta:
        managed = False
        db_table = 'v_compare_base_jockey'

    race_date = models.DateField(db_comment="レース日付", help_text="レース日付") 
    jockey_name = models.CharField(db_comment="騎手名", help_text="騎手名")
    jockey_url = models.CharField(db_comment="騎手URL", help_text="騎手URL")

# スクレイピング情報（加工用）
class BaseInfoView(models.Model):
    race_id = models.CharField(max_length=20)
    today_race_date = models.DateField()
    today_race_no = models.FloatField()
    place_id = models.SmallIntegerField()
    place_name = models.CharField(max_length=255)
    count = models.FloatField()
    field = models.CharField(max_length=1)
    distance = models.FloatField()
    horse_id = models.CharField(max_length=10)
    horse_name = models.CharField(max_length=255)
    frame_number = models.FloatField()
    horse_number = models.FloatField()
    sex = models.CharField(max_length=10)
    age = models.FloatField()
    weight = models.FloatField()
    body_weight = models.FloatField()
    jockey_id = models.CharField(max_length=20)
    jockey_name = models.CharField(max_length=255)
    WEIGHT_4KG_CUT_FLG = models.BooleanField()
    WEIGHT_3KG_CUT_FLG = models.BooleanField()
    WEIGHT_2KG_CUT_FLG = models.BooleanField()
    WEIGHT_1KG_CUT_FLG = models.BooleanField()
    WOMEN_WEIGHT_2KG_CUT_FLG = models.BooleanField()
    stable_name = models.CharField(max_length=255)
    odds = models.FloatField()
    popularity = models.FloatField()
    new_flg = models.BooleanField()
    not_win_flg = models.BooleanField()
    win_1_flg = models.BooleanField()
    win_2_flg = models.BooleanField()
    win_3_flg = models.BooleanField()
    g3_flg = models.BooleanField()
    g2_flg = models.BooleanField()
    g1_flg = models.BooleanField()
    l_flg = models.BooleanField()
    op_flg = models.BooleanField()
    is_win5 = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'v_base_info'

class HorseInfoView(models.Model):
    history_race_date = models.DateField()
    race_name = models.CharField(max_length=255)
    track_condition = models.CharField(max_length=50)
    weather = models.CharField(max_length=50)
    place_id = models.FloatField()
    place_name = models.CharField(max_length=255)
    count = models.FloatField()
    field = models.CharField(max_length=1)
    distance = models.FloatField()
    horse_id = models.CharField(max_length=20)
    body_weight = models.FloatField()
    frame_number = models.FloatField()
    horse_number = models.FloatField()
    jockey = models.CharField(max_length=255)
    rank = models.FloatField()
    time = models.FloatField()
    time_diff = models.FloatField()
    time_up = models.FloatField()
    pace_1 = models.FloatField()
    pace_2 = models.FloatField()
    position_1 = models.FloatField()
    position_2 = models.FloatField()
    position_3 = models.FloatField()
    position_4 = models.FloatField()
    odds = models.FloatField()
    popularity = models.FloatField()
    winner = models.CharField(max_length=255)
    prize = models.FloatField()
    new_flg = models.BooleanField()
    g1_flg = models.BooleanField()
    g2_flg = models.BooleanField()
    g3_flg = models.BooleanField()
    l_flg = models.BooleanField()
    not_win_flg = models.BooleanField()
    op_flg = models.BooleanField()
    win_1_flg = models.BooleanField()
    win_2_flg = models.BooleanField()
    win_3_flg = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'v_horse_info'

class ResultInfoView(models.Model):
    race_id = models.CharField(max_length=20)
    horse_number = models.FloatField()
    horse_name = models.CharField(max_length=255)
    rank = models.FloatField()
    race_time = models.FloatField()
    corner_order = models.CharField(max_length=255)
    date = models.DateField()
    positions = models.CharField(max_length=255)
    positions_tie = models.CharField(max_length=255)
    pay1 = models.FloatField()
    pay1_tie = models.FloatField()
    pay123_1 = models.FloatField()
    pay123_2 = models.FloatField()
    pay123_3 = models.FloatField()
    pay123_tie = models.FloatField()
    pay123_12_1 = models.FloatField()
    pay123_12_2 = models.FloatField()
    pay123_12_3 = models.FloatField()
    pay123_12_4_tie = models.FloatField()
    pay123_12_5_tie = models.FloatField()
    pay12_21 = models.FloatField()
    pay12_21_tie = models.FloatField()
    pay12_12 = models.FloatField()
    pay12_12_tie = models.FloatField()
    pay123_321 = models.FloatField()
    pay123_321_tie = models.FloatField()
    pay123_123 = models.FloatField()
    pay123_123_tie = models.FloatField()

    class Meta:
        managed = False
        db_table = 'v_result_info'

class JockeyInfoView(models.Model):
    history_race_date = models.DateField()
    history_race_no = models.FloatField()
    race_name = models.CharField(max_length=255)
    track_condition = models.CharField(max_length=50)
    weather = models.CharField(max_length=50)
    place_id = models.FloatField()
    place_name = models.CharField(max_length=255)
    count = models.FloatField()
    field = models.CharField(max_length=1)
    distance = models.FloatField()
    jockey_id = models.CharField(max_length=20)
    weight = models.FloatField()
    body_weight = models.FloatField()
    jockey_name = models.CharField(max_length=255)
    frame_number = models.FloatField()
    horse_number = models.FloatField()
    horse = models.CharField(max_length=255)
    rank = models.FloatField()
    time = models.FloatField()
    time_diff = models.FloatField()
    pace_1 = models.FloatField()
    pace_2 = models.FloatField()
    time_up = models.FloatField()
    position_1 = models.FloatField()
    position_2 = models.FloatField()
    position_3 = models.FloatField()
    position_4 = models.FloatField()
    odds = models.FloatField()
    popularity = models.FloatField()
    winner = models.CharField(max_length=255)
    prize = models.FloatField()
    WEIGHT_4KG_CUT_FLG = models.BooleanField()
    WEIGHT_3KG_CUT_FLG = models.BooleanField()
    WEIGHT_2KG_CUT_FLG = models.BooleanField()
    WEIGHT_1KG_CUT_FLG = models.BooleanField()
    WOMEN_WEIGHT_2KG_CUT_FLG = models.BooleanField()
    new_flg = models.BooleanField()
    win_1_flg = models.BooleanField()
    win_2_flg = models.BooleanField()
    win_3_flg = models.BooleanField()
    not_win_flg = models.BooleanField()
    g3_flg = models.BooleanField()
    g2_flg = models.BooleanField()
    g1_flg = models.BooleanField()
    l_flg = models.BooleanField()
    op_flg = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'v_jockey_info'

# region bk
# class HorseBloodMst(models.Model):
#     class Meta:
#         db_table = 'm_horse_blood'

#     id = models.AutoField(primary_key=True)
#     horse_id = models.CharField(max_length=20, db_comment="馬ID", help_text="馬ID")
#     horse_name = models.CharField(max_length=255, db_comment='馬名', help_text='馬名')

#     sire_1_male = models.CharField(max_length=255, null=True, db_comment='血統1世代目の雄', help_text='血統1世代目の雄')
#     sire_1_female = models.CharField(max_length=255, null=True, db_comment='血統1世代目の雌', help_text='血統1世代目の雌')
#     sire_2_1_male = models.CharField(max_length=255, null=True, db_comment='血統2-1世代目の雄', help_text='血統2-1世代目の雄')
#     sire_2_1_female = models.CharField(max_length=255, null=True, db_comment='血統2-1世代目の雌', help_text='血統2-1世代目の雌')
#     sire_2_2_male = models.CharField(max_length=255, null=True, db_comment='血統2-2世代目の雄', help_text='血統2-2世代目の雄')
#     sire_2_2_female = models.CharField(max_length=255, null=True, db_comment='血統2-2世代目の雌', help_text='血統2-2世代目の雌')

#     created_at = models.DateTimeField(db_comment="作成日時", help_text="作成日時")  
#     updated_at = models.DateTimeField(db_comment="更新日時", help_text="更新日時")  
#     created_user = models.CharField(max_length=255, null=True, db_comment="作成ユーザーID", help_text="作成ユーザーID")  
#     updated_user = models.CharField(max_length=255, null=True, db_comment="更新ユーザーID", help_text="更新ユーザーID")  

#     def __str__(self):
#         return f'{self.horse_id} - {self.horse_name}'


# ─── 売上・案件管理 ───────────────────────────────────────────────────────────
class SalesProject(models.Model):
    class Meta:
        db_table = 't_sales_project'
        ordering = ['-entry_month', 'cl_name']
        verbose_name = "案件"
        verbose_name_plural = "案件一覧"

    STATUS_CHOICES = [
        ('negotiating', '商談中'),
        ('ordered',     '受注済'),
        ('in_progress', '進行中'),
        ('completed',   '完了'),
        ('lost',        '失注'),
    ]

    id             = models.AutoField(primary_key=True)
    entry_month    = models.DateField(null=True, blank=True, db_comment="入金月")
    cl_name        = models.CharField(max_length=255, db_comment="CL名")
    project_name   = models.CharField(max_length=255, db_comment="案件名")
    sales_amount   = models.DecimalField(max_digits=12, decimal_places=0, default=0, db_comment="売上")
    outsource_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, db_comment="外注費")
    gross_profit   = models.DecimalField(max_digits=12, decimal_places=0, default=0, db_comment="粗利")
    gross_profit_rate = models.DecimalField(max_digits=5, decimal_places=1, default=0, db_comment="粗利率(%)")
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='negotiating', db_comment="ステータス")
    memo           = models.TextField(blank=True, default='', db_comment="メモ")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.gross_profit = self.sales_amount - self.outsource_amount
        if self.sales_amount and self.sales_amount > 0:
            self.gross_profit_rate = round(float(self.gross_profit) / float(self.sales_amount) * 100, 1)
        else:
            self.gross_profit_rate = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cl_name} - {self.project_name}"


# ─── 馬券記録・シミュレーション ───────────────────────────────────────────────
class BettingRecord(models.Model):
    """
    馬券購入記録モデル。実購入とシミュレーション両方に対応。
    """
    class Meta:
        db_table = 't_betting_record'
        ordering = ['-race_date', '-created_at']
        verbose_name = "馬券記録"
        verbose_name_plural = "馬券記録一覧"

    BET_TYPE_CHOICES = [
        ('win',       '単勝'),
        ('place',     '複勝'),
        ('quinella',  '馬連'),
        ('exacta',    '馬単'),
        ('wide',      'ワイド'),
        ('trio',      '3連複'),
        ('trifecta',  '3連単'),
    ]

    id            = models.AutoField(primary_key=True)
    race_id       = models.CharField(max_length=12, db_comment="レースID")
    race_date     = models.DateField(db_comment="レース日付")
    race_place    = models.CharField(max_length=20, null=True, blank=True, db_comment="開催場所")
    race_name     = models.CharField(max_length=100, null=True, blank=True, db_comment="レース名")
    race_number   = models.SmallIntegerField(null=True, blank=True, db_comment="レース番号")

    # 馬券情報
    bet_type      = models.CharField(max_length=20, choices=BET_TYPE_CHOICES, db_comment="馬券種別")
    combination   = models.CharField(max_length=30, db_comment="組み合わせ（例: 3-7, 1-2-5）")
    bet_amount    = models.IntegerField(default=100, db_comment="購入金額（円）")
    odds          = models.FloatField(null=True, blank=True, db_comment="オッズ")

    # 結果（nullは未確定）
    is_win        = models.BooleanField(null=True, blank=True, db_comment="的中フラグ")
    payout        = models.IntegerField(default=0, db_comment="払い戻し金額（円）")
    profit        = models.IntegerField(default=0, db_comment="損益（payout - bet_amount）")

    # 予測情報（モデルからの予測）
    predicted_rank_1   = models.SmallIntegerField(null=True, blank=True, db_comment="予測1着馬番")
    predicted_rank_2   = models.SmallIntegerField(null=True, blank=True, db_comment="予測2着馬番")
    predicted_rank_3   = models.SmallIntegerField(null=True, blank=True, db_comment="予測3着馬番")
    model_version      = models.CharField(max_length=50, null=True, blank=True, db_comment="使用モデルバージョン")

    # シミュレーション
    is_simulation = models.BooleanField(default=False, db_comment="シミュレーションフラグ")
    memo          = models.TextField(blank=True, default='', db_comment="メモ")

    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.profit = self.payout - self.bet_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.race_date} {self.race_id} {self.get_bet_type_display()} {self.combination}"
# endregion
