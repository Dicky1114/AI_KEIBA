from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_folder', '0024_alter_traininginfo_today_race_no'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesProject',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('entry_month', models.DateField(blank=True, db_comment='入金月', null=True)),
                ('cl_name', models.CharField(db_comment='CL名', max_length=255)),
                ('project_name', models.CharField(db_comment='案件名', max_length=255)),
                ('sales_amount', models.DecimalField(db_comment='売上', decimal_places=0, default=0, max_digits=12)),
                ('outsource_amount', models.DecimalField(db_comment='外注費', decimal_places=0, default=0, max_digits=12)),
                ('gross_profit', models.DecimalField(db_comment='粗利', decimal_places=0, default=0, max_digits=12)),
                ('gross_profit_rate', models.DecimalField(db_comment='粗利率(%)', decimal_places=1, default=0, max_digits=5)),
                ('status', models.CharField(
                    choices=[
                        ('negotiating', '商談中'),
                        ('ordered', '受注済'),
                        ('in_progress', '進行中'),
                        ('completed', '完了'),
                        ('lost', '失注'),
                    ],
                    db_comment='ステータス',
                    default='negotiating',
                    max_length=20,
                )),
                ('memo', models.TextField(blank=True, db_comment='メモ', default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '案件',
                'verbose_name_plural': '案件一覧',
                'db_table': 't_sales_project',
                'ordering': ['-entry_month', 'cl_name'],
            },
        ),
    ]
