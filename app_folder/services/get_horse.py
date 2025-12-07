# region "Library"

import pandas as pd
import os
from bs4 import BeautifulSoup
from urllib import request
import time
import datetime
from django.conf import settings
from io import StringIO
from django.conf import settings
from ..models import CompareBaseHorseView
from ..services.insert_db import insert_horse_db, insert_horse_blood_db
from celery_progress.backend import ProgressRecorder
# Grobal Varible
url_race_list = []
race_id_list = []

def horse_data(self, html_content, username, flg):
    try:
        # Defind the variable
        result_df = pd.DataFrame()
        horse_df = pd.DataFrame()
        horse_blood_df = pd.DataFrame()
        horse_links = []
        horse_name = '' 
        horse_url = ''
        columns_to_drop = ['映 像', '馬場 指数', 'ﾀｲﾑ 指数', '厩舎 ｺﾒﾝﾄ', '備考', 'R']

        # 馬情報メイン取得から呼びされた場合
        if flg == "horse":
            # 基本情報にある馬情報を取得
            horse_data_list = CompareBaseHorseView.objects.values('horse_name', 'horse_url', 'race_date')

            # for horse_data in tqdm(horse_data_list, desc="処理中"):
            progress_recorder = ProgressRecorder(self)
            total = len(horse_data_list)
            for i, horse_data in enumerate(horse_data_list):
                progress_recorder.set_progress(i + 1, total, f"{i+1}/{total} 件 処理中...")
                temp_horse_df = pd.DataFrame()
                temp_horse_blood_df = pd.DataFrame()

                # 変数作成
                horse_name = horse_data['horse_name']
                horse_url = horse_data['horse_url']
                before_max_date = horse_data['race_date']
                horse_id = horse_url.split("/")[4]
                max_date_str = before_max_date.strftime("%Y-%m-%d")
                max_date = datetime.datetime.strptime(max_date_str, "%Y-%m-%d")
                file_name = f'{horse_id}_{max_date_str}.html'
                save_file = os.path.join(f'{settings.MEDIA_ROOT}/horse', file_name)

                # ファイル名と取得レース日を比較して、以下であれば、読み込み
                match_file = [f for f in os.listdir(f'{settings.MEDIA_ROOT}/horse') if (horse_id in f and max_date == datetime.datetime.strptime(f.split('_')[1].split('.')[0], '%Y-%m-%d'))]
                
                if match_file:
                    with open(save_file, 'rb') as file:
                        html_content = file.read()
                    print(f'ファイル読込:{match_file}')
                    horse = pd.read_html(StringIO(html_content.decode('EUC-JP')))
                    temp_horse_df = pd.DataFrame(horse[2][:])
                    temp_horse_df = temp_horse_df.drop(columns=columns_to_drop)

                else:
                    try:
                        time.sleep(1)
                        match_file = [f for f in os.listdir(f'{settings.MEDIA_ROOT}/horse') if (horse_id in f and max_date > datetime.datetime.strptime(f.split('_')[1].split('.')[0], '%Y-%m-%d'))]
                        if match_file:
                            os.remove(match_file[0])

                        req = request.Request(horse_url, headers=settings.HEADERS)
                        response = request.urlopen(req)
                        html_content = response.read()
                        horse = pd.read_html(StringIO(html_content.decode('EUC-JP')))
                        
                        if len(horse) <= 2:
                            continue
                            
                        temp_horse_df = pd.DataFrame(horse[2][:])
                        temp_horse_df = temp_horse_df.drop(columns=columns_to_drop)
                        new_date = datetime.datetime.strptime(temp_horse_df.sort_values(by='日付', ascending=False).iloc[0]['日付'], "%Y/%m/%d")
                        new_date_str = new_date.strftime('%Y-%m-%d')
                        file_name = f'{horse_id}_{new_date_str}.html'

                        save_file = os.path.join(f'{settings.MEDIA_ROOT}/horse', file_name)
                        print(f'アクセス:{save_file}')
                        with open(save_file, 'wb') as file:
                            file.write(html_content)
                    except:
                        continue
                 
                temp_horse_df['日付']  = temp_horse_df['日付'].replace('/','-')
                temp_horse_df['new_flg']    = temp_horse_df['レース名'].str.contains('新馬').astype(int)
                temp_horse_df['win_1_flg']  = temp_horse_df['レース名'].str.contains('1勝').astype(int)
                temp_horse_df['win_2_flg']  = temp_horse_df['レース名'].str.contains('2勝').astype(int)
                temp_horse_df['win_3_flg']  = temp_horse_df['レース名'].str.contains('3勝').astype(int)
                temp_horse_df['not_win_flg'] = temp_horse_df['レース名'].str.contains('未勝利').astype(int)
                temp_horse_df['g3_flg']     = temp_horse_df['レース名'].str.contains('GⅢ').astype(int)
                temp_horse_df['g2_flg']     = temp_horse_df['レース名'].str.contains('GⅡ').astype(int)
                temp_horse_df['g1_flg']     = temp_horse_df['レース名'].str.contains('GI').astype(int)
                temp_horse_df['l_flg']      = temp_horse_df['レース名'].str.contains(r'\(L\)').astype(int)
                temp_horse_df['op_flg']     = temp_horse_df['レース名'].str.contains(r'\(OP\)').astype(int)
                temp_horse_df['horse_id'] = horse_id
                temp_horse_df['horse_name'] = horse_name

                # 競走馬の血統データ
                df = pd.DataFrame(horse[1])
                temp_horse_blood_df = pd.DataFrame([[
                    df.iloc[0, 0],  # blood_1_male
                    df.iloc[2, 0],  # blood_1_female
                    df.iloc[0, 1],  # blood_2_male
                    df.iloc[1, 1],  # blood_2_female
                    df.iloc[2, 1],  # blood_3_male
                    df.iloc[3, 1]   # blood_3_female
                ]], columns=settings.HORSE_BLOOD_COL)
                temp_horse_blood_df['horse_id'] = horse_id
                temp_horse_blood_df['horse_name'] = horse_name
                
                horse_df = pd.concat([horse_df, temp_horse_df], ignore_index=True)
                horse_blood_df = pd.concat([horse_blood_df, temp_horse_blood_df], ignore_index=True)


                horse_df.rename(columns=settings.NEW_HORSE_COL, inplace=True)
                horse_df = horse_df.drop_duplicates(subset=['horse_id', 'race_date'])
                insert_horse_db(horse_df, username)
                insert_horse_blood_db(horse_blood_df, username)
                horse_df = pd.DataFrame()
                horse_blood_df = pd.DataFrame()
            return

        # 基本情報取得から呼び出された場合
        else:
            # レース種別の付与
            soup = BeautifulSoup(html_content, 'html.parser')
            title_text = soup.title.string if soup.title else ""
            is_shinba  = 1 if "新馬"   in title_text else 0
            is_mishori = 1 if "未勝利" in title_text else 0
            is_1win    = 1 if "1勝"    in title_text or "１勝" in title_text else 0
            is_2win    = 1 if "2勝"    in title_text or "２勝" in title_text else 0
            is_3win    = 1 if "3勝"    in title_text or "３勝" in title_text else 0
            is_L       = 1 if "(L)"    in title_text else 0
            is_OP      = 1 if "(OP)"   in title_text else 0
            is_g3      = 1 if "G3"     in title_text else 0
            is_g2      = 1 if "G2"     in title_text else 0
            is_g1      = 1 if "G1"     in title_text else 0
            if soup.find('span', class_='Icon_GradeType Icon_GradeType13 Icon_GradePos01'):
                is_win5 = 1
            else:
                is_win5 = 0 

            # 馬情報のURLを取得
            horse_table = soup.find('table', class_='RaceTable01') 
            rows = horse_table.find_all('tr', class_='HorseList')
            for i, row in enumerate(rows):
                horse_info = row.find('td', class_='HorseInfo')
                horse_link = horse_info.find('a')
                horse_name = horse_link.text.strip()
                horse_url  = horse_link['href']
                horse_links.append({'horse_name': horse_name, 'horse_url': horse_url})
            
            result_df = pd.DataFrame(horse_links)
            return result_df, is_shinba, is_mishori, is_1win, is_2win, is_3win, is_g3, is_g2, is_g1, is_L, is_OP, is_win5, title_text 
        
    except Exception as e:
        print(e)
# endregion
