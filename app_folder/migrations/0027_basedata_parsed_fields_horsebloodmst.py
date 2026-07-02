"""
Migration: BaseDataに解析済みフィールド追加 + HorseBloodMstテーブル追加
@version 1.0.0  2026-04-03  新規作成 (Dicky1114)

追加内容:
- BaseData.age             : 年齢（性齢"牡3"から分離）
- BaseData.body_weight_diff: 馬体重増減（"480(-2)"から分離）
- BaseData.distance_m      : 距離メートル数（"芝1600m"から分離）
- BaseData.field_type      : コース種別 turf/dirt/jump（距離文字列から分離）
- HorseBloodMst            : 血統テーブル（父・母・父父・父母・母父・母母）
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    BaseDataに解析済みフィールド4つを追加。
    HorseBloodMst(m_horse_blood)はDB上に既存のため 0028 で --fake 適用。
    """

    dependencies = [
        ('app_folder', '0026_bettingrecord'),
    ]

    operations = [
        # ── BaseData: 解析済みフィールド追加 ──────────────────────────────
        migrations.AddField(
            model_name='basedata',
            name='age',
            field=models.SmallIntegerField(
                blank=True, null=True,
                db_comment='年齢', help_text='年齢（性齢から分離）'
            ),
        ),
        migrations.AddField(
            model_name='basedata',
            name='body_weight_diff',
            field=models.SmallIntegerField(
                blank=True, null=True,
                db_comment='馬体重増減', help_text='馬体重増減(kg)（例: -2）'
            ),
        ),
        migrations.AddField(
            model_name='basedata',
            name='distance_m',
            field=models.SmallIntegerField(
                blank=True, null=True,
                db_comment='距離(m)', help_text='距離メートル数（例: 1600）'
            ),
        ),
        migrations.AddField(
            model_name='basedata',
            name='field_type',
            field=models.CharField(
                blank=True, null=True, max_length=10,
                db_comment='コース種別', help_text='コース種別: turf/dirt/jump'
            ),
        ),
    ]
