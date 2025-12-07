# 修正済
# =========================================================
# # 概要        : 圧縮、解凍関連
# 改訂履歴       : 2025/04/29 初版
# =========================================================

#  【ライブラリ】ファイル名を変更する処理
import os
import re
import shutil
import zipfile
from datetime import datetime

#  【関数_00】ファイル名を変更する処理
def name_change(kaisai_date, zip_folder, race_id, tail) : 
    """ 【関数_00】ファイル名を変更する処理
        概要 : 
            ファイル名を変更する処理
        引数 : 
            kaisai_date : 解凍年月日
            zip_folder : Zip保存フォルダ（Media） 
            race_id : レースID
            tail : フォルダ末尾文字
        戻り値 : 
            None
    """    
    # 既存のファイルの名称を更新
    kaisai_date = datetime.strptime(kaisai_date, "%Y%m%d")
    kaisai_date_str = kaisai_date.strftime("%Y-%m-%d")
    old_filename = os.path.join(zip_folder, tail, f"{race_id}.html")
    new_filename = os.path.join(zip_folder, tail, f"{kaisai_date_str}_{race_id}.html")
    if os.path.exists(old_filename) : 
        shutil.move(old_filename, new_filename)

# 【関数_00】ファイル解凍ツール
def unzip_files(current_date, zip_folder, tail, horse) : 
    """ 【関数_00】ファイル解凍ツール
        概要 : 
            ファイルを解凍する処理
        引数 : 
            current_date : 解凍年月日
            zip_folder : Zip保存フォルダ（Media） 
            race_id : レースID
            tail : フォルダ末尾文字
        戻り値 : 
            None
    """
    # カレンダー情報の解凍
    if current_date == None : 
        for zip in os.listdir(os.path.join(zip_folder, tail)) : 
            if zip.endswith(".zip") : 
                zip_path = os.path.join(zip_folder,tail, os.path.basename(zip))
                with zipfile.ZipFile(zip_path, "r") as zip_ref : 
                    zip_ref.extractall(os.path.join(zip_folder, tail))
                os.remove(zip_path)
        return
    # 基本、結果情報の解凍
    elif len(current_date) == 4 : 
        for zip in os.listdir(os.path.join(zip_folder, tail)) : 
            if zip.startswith(current_date) and zip.endswith(".zip") : 
                zip_path = os.path.join(zip_folder,tail, os.path.basename(zip))
                with zipfile.ZipFile(zip_path, "r") as zip_ref : 
                    zip_ref.extractall(os.path.join(zip_folder, tail))
                os.remove(zip_path)
        return
    # 騎手情報の解凍するための情報を作成
    elif horse == None : 
        zip_file_name = current_date.strftime("%Y-%m") + ".zip"
    # 馬情報の解凍するための情報を作成
    else : 
        zip_file_name = horse
        
    # ファイル解凍
    zip_path = os.path.join(zip_folder, tail, zip_file_name)
    if os.path.exists(zip_path) : 
        with zipfile.ZipFile(zip_path, "r") as zip_ref : 
            zip_ref.extractall(os.path.join(zip_folder, tail))
        os.remove(zip_path)

# 【関数_00】ファイル圧縮ツール
def zip_files(zip_folder, tail) : 
    """ 【関数_00】ファイル圧縮ツール
        概要 : 
            ファイルを圧縮する処理
        引数 : 
            zip_folder : Zip保存フォルダ（Media） 
            race_id : レースID
            tail : フォルダ末尾文字
        戻り値 : 
            None
    """
    # htmlファイルがある場合、そのファイルパスをリストに追記
    html_files = [os.path.join(zip_folder, tail, file) for file in os.listdir(os.path.join(zip_folder, tail)) if file.endswith(".html")]
    
    # ファイルを月ごとに分類
    month_dict = {}
    for file in html_files : 
        if tail == "horse" or tail == "jockey" : 
            race_month = os.path.basename(file).split("_")[1][ : 7]
        else : 
            race_month = os.path.basename(file).split("_")[0][ : 7]

        if race_month : 
            if race_month not in month_dict : 
                month_dict[race_month] = []
            month_dict[race_month].append(file)

    # 月ごとに圧縮
    for month, files in month_dict.items() : 
        zip_name = f"{month}.zip"
        zip_path = os.path.join(zip_folder, tail, zip_name)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf : 
            for file in files : 
                zipf.write(file, os.path.basename(file))

        # ファイル名が正しい形式か確認
        if not re.match(r"^\d{4}-\d{2}\.zip$", zip_name) : 
            # 不正な形式の場合は削除
            os.remove(zip_path)

        # 圧縮後、元ファイルを削除
        for file in files : 
            os.remove(file)