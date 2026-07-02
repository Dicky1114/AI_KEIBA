"""
Migration: HorseBloodMstテーブル登録（--fake適用用）
@version 1.0.0  2026-04-03  新規作成 (Dicky1114)

m_horse_blood テーブルはDB上に既存のため、このマイグレーションは
`python manage.py migrate app_folder 0028 --fake` で適用すること。
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    HorseBloodMst(m_horse_blood)はDB上に既存のため --fake で適用。
    """

    dependencies = [
        ('app_folder', '0027_basedata_parsed_fields_horsebloodmst'),
    ]

    operations = [
        migrations.CreateModel(
            name='HorseBloodMst',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('horse_id', models.CharField(
                    db_comment='馬ID', help_text='馬ID', max_length=20
                )),
                ('horse_name', models.CharField(
                    db_comment='馬名', help_text='馬名', max_length=255
                )),
                ('sire_1_male', models.CharField(
                    db_comment='父', help_text='父', max_length=255, null=True
                )),
                ('sire_1_female', models.CharField(
                    db_comment='母', help_text='母', max_length=255, null=True
                )),
                ('sire_2_1_male', models.CharField(
                    db_comment='父父', help_text='父父', max_length=255, null=True
                )),
                ('sire_2_1_female', models.CharField(
                    db_comment='父母', help_text='父母', max_length=255, null=True
                )),
                ('sire_2_2_male', models.CharField(
                    db_comment='母父', help_text='母父', max_length=255, null=True
                )),
                ('sire_2_2_female', models.CharField(
                    db_comment='母母', help_text='母母', max_length=255, null=True
                )),
                ('created_at', models.DateTimeField(
                    db_comment='作成日時', help_text='作成日時'
                )),
                ('updated_at', models.DateTimeField(
                    db_comment='更新日時', help_text='更新日時'
                )),
                ('created_user', models.CharField(
                    db_comment='作成ユーザーID', help_text='作成ユーザーID',
                    max_length=255, null=True
                )),
                ('updated_user', models.CharField(
                    db_comment='更新ユーザーID', help_text='更新ユーザーID',
                    max_length=255, null=True
                )),
            ],
            options={
                'db_table': 'm_horse_blood',
            },
        ),
    ]
