"""
Migration: BettingRecord (馬券記録) モデル追加
@version 1.0.0  2026-03-30  新規作成 (Dicky1114)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_folder', '0025_salesproject'),
    ]

    operations = [
        migrations.CreateModel(
            name='BettingRecord',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('race_id', models.CharField(db_comment='レースID', max_length=12)),
                ('race_date', models.DateField(db_comment='レース日付')),
                ('race_place', models.CharField(blank=True, db_comment='開催場所', max_length=20, null=True)),
                ('race_name', models.CharField(blank=True, db_comment='レース名', max_length=100, null=True)),
                ('race_number', models.SmallIntegerField(blank=True, db_comment='レース番号', null=True)),
                ('bet_type', models.CharField(
                    choices=[
                        ('win', '単勝'),
                        ('place', '複勝'),
                        ('quinella', '馬連'),
                        ('exacta', '馬単'),
                        ('wide', 'ワイド'),
                        ('trio', '3連複'),
                        ('trifecta', '3連単'),
                    ],
                    db_comment='馬券種別',
                    max_length=20,
                )),
                ('combination', models.CharField(db_comment='組み合わせ（例: 3-7, 1-2-5）', max_length=30)),
                ('bet_amount', models.IntegerField(db_comment='購入金額（円）', default=100)),
                ('odds', models.FloatField(blank=True, db_comment='オッズ', null=True)),
                ('is_win', models.BooleanField(blank=True, db_comment='的中フラグ', null=True)),
                ('payout', models.IntegerField(db_comment='払い戻し金額（円）', default=0)),
                ('profit', models.IntegerField(db_comment='損益（payout - bet_amount）', default=0)),
                ('predicted_rank_1', models.SmallIntegerField(blank=True, db_comment='予測1着馬番', null=True)),
                ('predicted_rank_2', models.SmallIntegerField(blank=True, db_comment='予測2着馬番', null=True)),
                ('predicted_rank_3', models.SmallIntegerField(blank=True, db_comment='予測3着馬番', null=True)),
                ('model_version', models.CharField(blank=True, db_comment='使用モデルバージョン', max_length=50, null=True)),
                ('is_simulation', models.BooleanField(db_comment='シミュレーションフラグ', default=False)),
                ('memo', models.TextField(blank=True, db_comment='メモ', default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '馬券記録',
                'verbose_name_plural': '馬券記録一覧',
                'db_table': 't_betting_record',
                'ordering': ['-race_date', '-created_at'],
            },
        ),
    ]
