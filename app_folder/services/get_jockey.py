# region "Library"

import time
import pandas as pd
from tqdm import tqdm
import datetime
from bs4 import BeautifulSoup
from urllib import request
import time
from ..services.insert_db import insert_jockey_db
from ..models import CompareBaseJockeyView
from django.conf import settings
from io import StringIO
from urllib.parse import urlparse, parse_qs

# ２段を１段の列に変換
def convert_column_name(col):
    if col[0] == col[1]:
        return col[0]
    else:
        return f"{col[0]}_{col[1]}"

def jockey_data(html_content, username, flg):
    try:
        # 変数宣言
        result_df = pd.DataFrame()
        jockey_df = pd.DataFrame()
        jockey_links = []
        jockey_name = '' 
        jockey_url = ''
        i = 0
        columns_to_drop = ['映 像']

        # 騎手データ取得処理
        if flg == "jockey":
            # レース情報にあって、騎手情報にない騎手IDを取得
            jockey_data_list = CompareBaseJockeyView.objects.values('jockey_name', 'jockey_url', 'race_date')

            # 取得した騎手情報でループ処理
            for jockey_data in tqdm(jockey_data_list, desc="騎手毎"):
                # 変数作成
                jockey_name = jockey_data['jockey_name']
                jockey_url_pre = jockey_data['jockey_url'][:-1]

                # # URLを解析
                parsed_url = urlparse(jockey_url_pre)
                query_params = parse_qs(parsed_url.query)
                jockey_id = query_params.get('id', [None])[0]

                req = request.Request(jockey_data['jockey_url'], headers=settings.HEADERS)
                response = request.urlopen(req)
                html_content = response.read()
                soup = BeautifulSoup(html_content, 'html.parser')
                a_tag = soup.find('a', title="最後")
                if a_tag == None:
                    page_value = 2
                else:
                    url = a_tag['href']
                    parsed_url = urlparse(url)
                    query_params = parse_qs(parsed_url.query)
                    page_value = query_params.get('page', [None])[0]

                for page in tqdm(range (1, int(page_value)), desc="ページ毎"):
                    temp_jockey_df = pd.DataFrame()
                    time.sleep(1)
                    jockey_url = jockey_url_pre + str(page)
                    try:
                        req = request.Request(jockey_url, headers=settings.HEADERS)
                        response = request.urlopen(req)
                        html_content = response.read()
                        jockey = pd.read_html(StringIO(html_content.decode('EUC-JP', errors='ignore')))
                    except Exception as e:
                        print(e)
                        return
                    temp_jockey_df = pd.DataFrame(jockey[0][:])
                    temp_jockey_df = temp_jockey_df.drop(columns=columns_to_drop)
                    new_date = datetime.datetime.strptime(temp_jockey_df.sort_values(by='日付', ascending=False).iloc[0]['日付'], "%Y/%m/%d")
                    new_date_str = new_date.strftime('%Y-%m-%d')
                    temp_jockey_df['日付'] = temp_jockey_df['日付'].str.replace("/", "-", regex=False)

                    if page_value == 2 or new_date_str[:4] == '2018':
                        break
                
                    temp_jockey_df['レース名'] = temp_jockey_df['レース名'].fillna('')
                    temp_jockey_df['new_flg']    = temp_jockey_df['レース名'].str.contains('新馬').astype(int)
                    temp_jockey_df['win_1_flg']  = temp_jockey_df['レース名'].str.contains('1勝').astype(int)
                    temp_jockey_df['win_2_flg']  = temp_jockey_df['レース名'].str.contains('2勝').astype(int)
                    temp_jockey_df['win_3_flg']  = temp_jockey_df['レース名'].str.contains('3勝').astype(int)
                    temp_jockey_df['not_win_flg'] = temp_jockey_df['レース名'].str.contains('未勝利').astype(int)
                    temp_jockey_df['g3_flg']     = temp_jockey_df['レース名'].str.contains('GⅢ').astype(int)
                    temp_jockey_df['g2_flg']     = temp_jockey_df['レース名'].str.contains('GⅡ').astype(int)
                    temp_jockey_df['g1_flg']     = temp_jockey_df['レース名'].str.contains('GI').astype(int)
                    temp_jockey_df['l_flg']      = temp_jockey_df['レース名'].str.contains(r'\(L\)').astype(int)
                    temp_jockey_df['op_flg']     = temp_jockey_df['レース名'].str.contains(r'\(OP\)').astype(int)
                    temp_jockey_df['jockey_id']  = jockey_id
                    temp_jockey_df['jockey_name'] = jockey_name

                    temp_jockey_df.rename(columns=settings.NEW_JOCKEY_COL, inplace=True)
                    temp_jockey_df['race'] = temp_jockey_df['race'].apply(lambda x: str(x).strip())
                    temp_jockey_df = temp_jockey_df.dropna(subset=['race_date'])
                    finish_flg = insert_jockey_db(temp_jockey_df, username)
                    response.close()
                    if finish_flg:
                        finish_flg = False
                        print(new_date_str)
                        break
            return

        # 基本情報取得から呼び出された場合
        else:
            # レース種別の付与
            soup = BeautifulSoup(html_content, 'html.parser')
            jockey_table = soup.find('table', class_='RaceTable01')
            rows = jockey_table.find_all('tr', class_='HorseList')
            for i, row in enumerate(rows):
                jockey_info = row.find('td', class_='Jockey')
                jockey_link = jockey_info.find('a')
                jockey_name = jockey_link.text.strip()
                jockey_url  = (jockey_link['href'][:-1] + '&page=1').replace('jockey/result/recent/','/?pid=jockey_detail&id=')
                jockey_links.append({'jockey_name': jockey_name, 'jockey_url': jockey_url})


            # 'RaceData01' クラスを持つ div 要素を特定
            race_data_div1 = soup.find('div', class_='RaceData01')
            distance = race_data_div1.find('span', text=lambda x: x and '0m' in x).text.strip()
            weather = race_data_div1.find(text=lambda x: x and '天候:' in x).split(':')[1].strip()
            track_condition = race_data_div1.find(text=lambda x: x and '馬場:' in x).split(':')[1].strip()
            # 'RaceData02' クラスを持つ div 要素を特定
            race_data_div2 = soup.find('div', class_='RaceData02')
            spans = race_data_div2.find_all('span')
            race_place = spans[1].text
            count = spans[7].text.replace('頭','')
            result_df = pd.DataFrame(jockey_links)
            return result_df, distance, weather, track_condition, race_place, count
        
    except Exception as e:
        print(e)