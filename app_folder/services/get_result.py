# region "Library"
import random
import time
import pandas as pd
import os
from bs4 import BeautifulSoup
from urllib import request
import time
from django.conf import settings
from io import StringIO
import glob
from django.conf import settings

def change_user_agent(user_agents):
    random_user_agent = random.choice(user_agents)
    h = {'User-Agent': random_user_agent}
    return h

def find_file_with_race_id(race_id, result_path):
    # HTML ファイルかつ race_id を含むものを検索
    pattern = os.path.join(result_path, f"*{race_id}*.html")
    files = glob.glob(pattern)
    return files[0] if files else None

def result(url, race_id, action):
    # 変数定義
    result_df = pd.DataFrame()
    html_content = ''
    ref_flg = False
    url = url.replace('shutuba', 'result')
    save_file = os.path.join(settings.MEDIA_ROOT,'odds', f'{race_id}.html')

    # ファイル存在チェック
    result_path = os.path.join(settings.MEDIA_ROOT, 'odds')
    file_path = find_file_with_race_id(race_id, result_path)

    # 参照ファイルが存在した場合
    if file_path:
        with open(file_path, 'r', encoding='EUC-JP', errors='ignore') as f:
            html_content = f.read()
            
    # 参照ファイルが存在しない場合
    if html_content == '':
        time.sleep(1)  
        header = change_user_agent(settings.USER_AGENTS)
        req = request.Request(url, headers=header)
        response = request.urlopen(req)
        html_content = response.read().decode('EUC-JP', errors='ignore')
        ref_flg = True
        with open(save_file, 'w', encoding='EUC-JP', errors='ignore') as f:
            f.write(html_content)

    # 開催日の取得
    soup = BeautifulSoup(html_content, 'html.parser')
    active_dd = soup.find('dd', class_='Active')
    if active_dd:
        a_tag = active_dd.find('a')
        if a_tag and 'href' in a_tag.attrs:
            href_value = a_tag['href']
            kaisai_date = None
            # `?`で区切られているか確認
            if '?' in href_value:
                query_params = href_value.split('?', 1)[1].split('&')  # クエリ部分を分離
                for param in query_params:
                    if 'kaisai_date' in param:
                        kaisai_date = param.split('=')[1]
                        break

    # 基本情報から呼び出されている場合、開催日のみ返す
    if action == "base":
        return result_df, kaisai_date, False

    # 結果情報から呼び出せれている場合、処理継続
    basis = pd.read_html(StringIO(html_content))
    basis_df = pd.DataFrame(basis[0])
    basis_df['race_id'] = race_id
    basis_df = basis_df[settings.RESULT_COL]
    basis_df.rename(columns=settings.NEW_RESULT_COL, inplace=True)
    df1 = pd.DataFrame(basis[1])
    df2 = pd.DataFrame(basis[2])
    # 事前準備
    result = {}
    result['race_date'] = kaisai_date
    result['race_id'] = race_id
    value = df2.loc[df2[0] == '3連単', 1].values[0]
    split = [item for item in value.split(' ') if item]
    positions = []

    # 着順
    for i in range(0, len(split), 3):
        group = split[i:i+3]
        positions.append('>'.join(group))
    if len(positions) > 1:
        result['positions'] = positions[0]
        result['positions_tie'] = positions[1]
    elif len(positions) == 1:
        result['positions'] = positions[0]
        result['positions_tie'] = ''
    else:
        result['positions'] = ''
        result['positions_tie'] = ''

    # 払戻金-複勝
    value = df1.loc[df1[0] == '複勝', 2].values[0]
    split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
    result['pay123_1'] = split[0]
    result['pay123_2'] = split[1]
    if len(split) == 2:
        result['pay123_3'] = ''
        result['pay123_tie'] = ''
    elif len(split) == 3:
        if '枠連' in df1[0].values:
            result['pay123_3'] = split[2]
            result['pay123_tie'] = ''
        else:
            result['pay123_3'] = ''
            result['pay123_tie'] = split[2]
    else:
        result['pay123_3'] = split[2]
        result['pay123_tie'] = split[3]

    # 払戻金-単勝、2連単、2連複、3連単、3連複
    value = df1.loc[df1[0] == '単勝', 2].values[0]
    split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
    value1 = df2.loc[df2[0] == '馬単', 2].values[0]
    split1 = [item.replace('円', '').replace(',', '') for item in value1.split(' ') if item]
    value2 = df1.loc[df1[0] == '馬連', 2].values[0]
    split2 = [item.replace('円', '').replace(',', '') for item in value2.split(' ') if item]
    value3 = df2.loc[df2[0] == '3連単', 2].values[0]
    split3 = [item.replace('円', '').replace(',', '') for item in value3.split(' ') if item]
    value4 = df2.loc[df2[0] == '3連複', 2].values[0]
    split4 = [item.replace('円', '').replace(',', '') for item in value4.split(' ') if item]
    result['pay1'] = split[0]
    result['pay12_12'] = split1[0]
    result['pay12_21'] = split2[0]
    result['pay123_123'] = split3[0]
    result['pay123_321'] = split4[0]
    if len(split) > 1:
        result['pay1_tie'] = split[1]
    else:
        result['pay1_tie'] = ''

    if len(split1) > 1:
        result['pay12_12_tie'] = split1[1]
    else:
        result['pay12_12_tie'] = ''

    if len(split2) > 1:
        result['pay12_21_tie'] = split2[1]
    else:
        result['pay12_21_tie'] = ''

    if len(split3) > 1:
        result['pay123_123_tie'] = split3[1]
    else:
        result['pay123_123_tie'] = ''

    if len(split4) > 1:
        result['pay123_321_tie'] = split4[1]
    else:
        result['pay123_321_tie'] = ''

    # 払戻金-ワイド
    value = df2.loc[0, 2]
    split = [item.replace('円', '').replace(',', '') for item in value.split(' ') if item]
    result['pay123_12_1'] = split[0]
    result['pay123_12_2'] = split[1]
    result['pay123_12_3'] = split[2]
    if len(split) > 3:
        result['pay123_12_4_tie'] = split[3]
        result['pay123_12_5_tie'] = ''
    elif len(split) > 4:
        result['pay123_12_4_tie'] = split[3]
        result['pay123_12_5_tie'] = split[4]
    else:
        result['pay123_12_4_tie'] = ''
        result['pay123_12_5_tie'] = ''
        
    # 結果をデータフレームに変換
    result_df = pd.DataFrame([result])
    basis_df = basis_df.merge(result_df, on=['race_id'], how='inner')
    
    return basis_df, kaisai_date, ref_flg