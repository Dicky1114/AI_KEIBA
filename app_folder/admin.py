from django.contrib import admin
from .models import URLMst, BaseData, ResultData, HorseData, JockeyData, TrainingInfo

from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django.shortcuts import render
from django.contrib.admin import AdminSite
from django.urls import path

class CusAdminSite(AdminSite):
    site_header = "【管理画面】競馬予測ツール"
        
    def get_urls(self):
        from .views.admin_scraping import scraping_view
        from .views.admin_training import training_view
        urls = super().get_urls()
        custom_urls = [
            path("scraping/", self.admin_view(scraping_view), name="scraping"),
            path("training/", self.admin_view(training_view), name="training"),
        ]
        return custom_urls + urls
    
    def get_app_list(self, request):
        """
        管理画面サイドバーのアプリとモデルの表示順をカスタマイズ
        """
        app_list = super().get_app_list(request)

        # 並び順を指定（app_label → models の順）
        desired_order = {
            'app_folder': [
                'UrlMst',
                'BaseData',
                'ResultData',
                'HorseData',
                'JockeyData',
                'TrainingInfo', 
            ],
        }

        # 再構築されたアプリリスト
        ordered = []
        for app in app_list:
            label = app['app_label']
            if label in desired_order:
                # モデル順を指定
                ordered_models = []
                for model_name in desired_order[label]:
                    for model in app['models']:
                        if model['object_name'] == model_name:
                            ordered_models.append(model)
                app['models'] = ordered_models
            ordered.append(app)

        return ordered

class RaceResource(resources.ModelResource):
    class Meta:
        model = URLMst
        skip_unchanged = True
        report_skipped = False
        fields = ('id', 'race_id', 'race_date', 'url', 'created_at', 'updated_at', 'created_user', 'updated_user')

class URLAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = RaceResource
    list_display = ('race_date', 'url_link', 'race_id', 'updated_at') 
    list_filter = ('race_date', 'race_id', 'updated_at')
    search_fields = ('race_date', 'race_id', 'updated_at')
    # フィールドの順番をカスタマイズ
    fieldsets = (
        ("必須項目", {
            'fields': ('race_date', 'race_id', 'url', 'created_at', 'updated_at'),
            'classes': (),
        }),
        ('任意項目', {
            'fields': ('created_user', 'updated_user'),
            'classes': ('collapse',),
        }),
    )
    
    def url_link(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)

    url_link.short_description = 'URL'

class BaseAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('race_date', 'race_id', 'horse_name', 'jockey_name', 'updated_at') 
    search_fields = ('race_date', 'race_id', 'horse_name', 'jockey_name', 'updated_at')
    list_filter = ('race_date', 'race_id', 'horse_name', 'jockey_name', 'updated_at')
        # フィールドの順番をカスタマイズ
    fieldsets = (
        ("必須項目", {
            'fields': ('race_id'
                        ,'horse_number'
                        ,'horse_name'
                        ,'race_date'
                        ,'new_flg'
                        ,'not_win_flg'
                        ,'win_1_flg'
                        ,'win_2_flg'
                        ,'win_3_flg'
                        ,'g3_flg'
                        ,'g2_flg'
                        ,'g1_flg'
                        ,'l_flg'
                        ,'op_flg'
                        ,'is_win5'
                        ,'created_at'
                        ,'updated_at'
                        ),
            'classes': (),
        }),
        ('任意項目', {
            'fields': ( 'event_title'
                        ,'frame_number'
                        ,'body_weight'
                        ,'jockey_name'
                        ,'stable_name'
                        ,'weight_change'
                        ,'odds'
                        ,'popularity'
                        ,'race_place'
                        ,'sex'
                        ,'weight'
                        ,'created_user'
                        ,'updated_user'
                        ),
            'classes': ('collapse',),
        }),
    )

class ResultAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('race_date', 'race_id', 'positions', 'pay123_123', 'updated_at') 
    search_fields = ('race_date', 'race_id', 'horse_number', 'horse_name', 'updated_at')
    list_filter = ('race_date', 'race_id', 'horse_number', 'horse_name', 'updated_at')
        # フィールドの順番をカスタマイズ
    fieldsets = (
        ("必須項目", {
            'fields': ('race_id'
                    ,'horse_number'
                    ,'horse_name'
                    ,'rank'
                    ,'race_time'
                    ,'corner_order'
                    ,'race_date'
                    ,'positions'
                    ,'pay1'
                    ,'pay123_1'
                    ,'pay123_2'
                    ,'pay123_3'
                    ,'pay123_12_1'
                    ,'pay123_12_2'
                    ,'pay123_12_3'
                    ,'pay12_21'
                    ,'pay12_12'
                    ,'pay123_321'
                    ,'pay123_123'
                    ,'created_at'
                    ,'updated_at'
                    ),
            'classes': (),
        }),
        ('任意項目', {
            'fields': ('positions_tie'                 
                        ,'pay1_tie'              
                        ,'pay123_tie'                
                        ,'pay123_12_4_tie'
                        ,'pay123_12_5_tie'               
                        ,'pay12_21_tie'            
                        ,'pay12_12_tie'                     
                        ,'pay123_321_tie'
                        ,'pay123_123_tie'
                        ,'created_user'
                        ,'updated_user'
                        ),
            'classes': ('collapse',),
        }),
    )

class HorseAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    # 表示する列（データ一覧で表示するフィールド）
    list_display = (
        'race_date', 'horse_id', 'horse_name', 'rank', 'race_place', 'weather', 'odds', 'popularity', 'updated_at'
    )

    # 検索フィールド（管理画面で検索するフィールド）
    search_fields = (
        'race_date', 'horse_id', 'horse_name', 'race_name', 'jockey', 'updated_at'
    )

    # フィルタリングフィールド（管理画面の右側のフィルターボックスで使用）
    list_filter = (
        'race_date', 'race_place', 'rank', 'weather', 'race_name', 'jockey', 'updated_at'
    )

    # フィールドの順番をカスタマイズ（フォーム表示時の順番）
    fieldsets = (
        ("必須項目", {
            'fields': (
                'horse_id', 'horse_name', 'race_date', 'race_place', 'weather', 'race_name', 'horse_number',
                'rank', 'jockey', 'odds', 'popularity', 'time', 'position', 'pace', 'winner', 'prize', 'new_flg',
                'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg', 'created_at', 'updated_at'
            ),
            'classes': ('wide',),
        }),
        ('任意項目', {
            'fields': (
                'count', 'frame', 'distance', 'track_condition', 'time_diff', 'body_weight', 'up',
                'win_1_flg', 'win_2_flg', 'win_3_flg', 'not_win_flg', 'pay1', 'pay123_1', 'pay123_2', 'pay123_3',
                'created_user', 'updated_user'
            ),
            'classes': ('collapse',),
        }),
    )

class JockeyAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    # 表示する列（データ一覧で表示するフィールド）
    list_display = (
        'race_date', 'jockey_id', 'jockey_name', 'race', 'rank', 'race_place', 'weather', 'odds', 'popularity', 'updated_at'
    )

    # 検索フィールド（管理画面で検索するフィールド）
    search_fields = (
        'race_date', 'jockey_id', 'jockey_name', 'race_name', 'updated_at'
    )

    # フィルタリングフィールド（管理画面の右側のフィルターボックスで使用）
    list_filter = (
        'race_date', 'race', 'rank', 'weather', 'race_place', 'jockey_name', 'updated_at'
    )

    # フィールドの順番をカスタマイズ（フォーム表示時の順番）
    fieldsets = (
        ("必須項目", {
            'fields': (
                'jockey_id', 'jockey_name', 'race_date', 'race_place', 'weather', 'race', 'race_name',
                'horse_number', 'rank', 'horse', 'weight', 'odds', 'popularity', 'time', 'position', 'pace',
                'winner', 'prize', 'new_flg', 'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg', 'created_at', 'updated_at'
            ),
            'classes': ('wide',),
        }),
        ('任意項目', {
            'fields': (
                'count', 'frame', 'distance', 'track_condition', 'time_diff', 'body_weight', 'up',
                'win_1_flg', 'win_2_flg', 'win_3_flg', 'not_win_flg', 'pay1', 'pay123_1', 'pay123_2', 'pay123_3',
                'created_user', 'updated_user'
            ),
            'classes': ('collapse',),
        }),
    )

class TrainingAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    # 表示する列（データ一覧で表示するフィールド）
    list_display = (
        'race_id', 'today_race_date', 'today_race_no', 'horse', 'jockey', 'rank'
    )

    # 検索フィールド（管理画面で検索するフィールド）
    search_fields = (
        'race_date', 'jockey_id', 'jockey_name', 'race_name', 'updated_at'
    )

    # フィルタリングフィールド（管理画面の右側のフィルターボックスで使用）
    list_filter = (
        'race_id', 'today_race_date', 'today_race_no', 'horse', 'jockey', 'rank'
    )

# モデルの登録
# AdminSiteのインスタンスを作る
# admin_site = CusAdminSite()
admin_site = CusAdminSite(name='custom_admin')
admin_site.register(URLMst, URLAdmin)
admin_site.register(BaseData, BaseAdmin)
admin_site.register(ResultData, ResultAdmin)
admin_site.register(HorseData, HorseAdmin)
admin_site.register(JockeyData, JockeyAdmin)
admin_site.register(TrainingInfo, TrainingAdmin)