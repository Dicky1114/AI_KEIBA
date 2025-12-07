from ..models import URLMst, BaseData, ResultData, HorseData, JockeyData
from django.utils import timezone
from django.db import connection

def insert_url_db(url_df, user_name):
    """
    取得したデータフレームを元にurl_matに追加・更新

    Parameters:
    ----------
    url_df : DataFrame
        URL情報
    user_name : str
        ログインユーザー
        
    """
    # region "取得したデータフレームを元にurl_matに追加・更新"

    for i, row in url_df.iterrows():
        URLMst.objects.update_or_create(
            race_id=row['race_id'],
            defaults={
                'race_date': row['race_date'],
                'url': row['url'],
                'created_at': timezone.now(),
                'updated_at': timezone.now(),
                'created_user': user_name,
                'updated_user': user_name,
            }
        )

    # endregion

def insert_base_db(basis_df, user_name):
    """
    取得したデータフレームを元にbase_infoに追加・更新

    Parameters:
    ----------
    url_df : DataFrame
        URL情報
    user_name : str
        ログインユーザー
        
    """
    # region "取得したデータフレームを元にbase_infoに追加・更新"

    for i, row in basis_df.iterrows():
        try:
            # 現在のレコードを取得
            existing_record = BaseData.objects.filter(
                race_id=row['race_id'],
                horse_number=row['horse_number']
            ).first()

            if existing_record:
                # すべてのフィールドが一致するか確認
                is_different = any(
                    getattr(existing_record, field) != row[field]
                    for field in [
                        'race_date', 'event_title', 'frame_number', 
                        'horse_name', 'sex', 'weight', 'body_weight', 
                        'jockey_name', 'stable_name', 'odds', 'race_place','count',
                        'popularity', 'new_flg','distance','weather','track_condition',
                        'win_1_flg', 'win_2_flg', 'win_3_flg',
                        'not_win_flg', 'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg', 'is_win5', 'horse_url', 'jockey_url'
                    ]
                )

                if is_different:
                    # 差分があれば更新
                    for field in [
                        'race_date', 'event_title', 'frame_number', 
                        'horse_name', 'sex', 'weight', 'body_weight', 
                        'jockey_name', 'stable_name', 'odds', 'race_place','count',
                        'popularity', 'new_flg','distance','weather','track_condition',
                        'win_1_flg', 'win_2_flg', 'win_3_flg',
                        'not_win_flg', 'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg' ,'is_win5', 'horse_url', 'jockey_url'
                    ]:
                        setattr(existing_record, field, row[field])
                    
                    existing_record.updated_at = timezone.now()
                    existing_record.updated_user = user_name
                    existing_record.save()
            else:
                # 完全に新しいレコードの場合、作成
                BaseData.objects.create(
                    race_id=row['race_id'],
                    horse_number=row['horse_number'],
                    race_date=row['race_date'],
                    event_title=row['event_title'],
                    frame_number=row['frame_number'],
                    horse_name=row['horse_name'],
                    sex=row['sex'],
                    weight=row['weight'],
                    body_weight=row['body_weight'],
                    jockey_name=row['jockey_name'],
                    stable_name=row['stable_name'],
                    odds=row['odds'],
                    popularity=row['popularity'],
                    new_flg=row['new_flg'],
                    not_win_flg=row['not_win_flg'],
                    win_1_flg=row['win_1_flg'],
                    win_2_flg=row['win_2_flg'],
                    win_3_flg=row['win_3_flg'],
                    g3_flg=row['g3_flg'],
                    g2_flg=row['g2_flg'],
                    g1_flg=row['g1_flg'],
                    l_flg=row['l_flg'],
                    op_flg=row['op_flg'],
                    is_win5=row['is_win5'],
                    horse_url=row['horse_url'],
                    jockey_url=row['jockey_url'],
                    distance = row['distance'],
                    weather = row['weather'],
                    track_condition = row['track_condition'],
                    race_place = row['race_place'],
                    count = row['count'],
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                    created_user=user_name,
                    updated_user=user_name
                )
        except Exception as e:
            print(f"エラーが発生しました: {e}")

# endregion

def insert_horse_blood_db(horse_df, user_name):
    """
    取得したデータフレームを元にhorse_infoに追加・更新

    Parameters:
    ----------
    horse_df : DataFrame
        馬データ情報
    user_name : str
        ログインユーザー
    """
    # region "取得したデータフレームを元にhorse_infoに追加・更新"
    for i, row in horse_df.iterrows():
        try:
            # 既存のレコードを取得
            
            existing_record = HorseBloodMst.objects.filter(
                horse_id=row['horse_id'], horse_name=row['horse_name']
            ).first()

            if existing_record:
                # 更新処理: データが異なる場合のみ更新
                is_different = any(
                    getattr(existing_record, field) != row.get(field, None)
                    for field in [
                        'sire_1_male', 'sire_1_female',
                        'sire_2_1_male', 'sire_2_1_female',
                        'sire_2_2_male', 'sire_2_2_female'
                    ]
                )

                if is_different:
                    # 差分があればフィールドを更新
                    for field in [
                        'sire_1_male', 'sire_1_female',
                        'sire_2_1_male', 'sire_2_1_female',
                        'sire_2_2_male', 'sire_2_2_female'
                    ]:
                        setattr(existing_record, field, row.get(field, None))
                    
                    existing_record.updated_at = timezone.now()
                    existing_record.updated_user = user_name
                    existing_record.save()

            else:
                # 新規作成
                HorseBloodMst.objects.create(
                    horse_id=row['horse_id'],
                    horse_name=row['horse_name'],
                    sire_1_male=row['sire_1_male'],
                    sire_1_female=row['sire_1_female'],
                    sire_2_1_male=row['sire_2_1_male'],
                    sire_2_1_female=row['sire_2_1_female'],
                    sire_2_2_male=row['sire_2_2_male'],
                    sire_2_2_female=row['sire_2_2_female'],
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                    created_user=user_name,
                    updated_user=user_name
                )

        except Exception as e:
            print(f"エラーが発生しました (行 {i}{field}): {e}")

# endregion

def insert_horse_db(horse_df, user_name):
    """
    取得したデータフレームを元にhorse_infoに追加・更新

    Parameters:
    ----------
    horse_df : DataFrame
        馬データ情報
    user_name : str
        ログインユーザー
    """
    # region "取得したデータフレームを元にhorse_infoに追加・更新"
    for i, row in horse_df.iterrows():
        try:
            # 既存のレコードを取得
            
            existing_record = HorseData.objects.filter(
                horse_id=row['horse_id'], race_date=row['race_date']
            ).first()

            if existing_record:
                
                # 更新処理: データが異なる場合のみ更新
                is_different = any(
                    getattr(existing_record, field) != row.get(field, None)
                    for field in [
                        'race_place', 'weather', 'race_name', 'horse_number',
                        'count', 'frame', 'odds', 'popularity', 'rank',
                        'jockey', 'weight', 'distance', 'track_condition',
                        'time', 'time_diff', 'position', 'pace', 'up',
                        'body_weight', 'winner', 'prize', 'new_flg',
                        'win_1_flg', 'win_2_flg', 'win_3_flg',
                        'not_win_flg', 'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg'
                    ]
                )

                if is_different:
                    # 差分があればフィールドを更新
                    for field in [
                        'race_place', 'weather', 'race_name', 'horse_number',
                        'count', 'frame', 'odds', 'popularity', 'rank',
                        'jockey', 'weight', 'distance', 'track_condition',
                        'time', 'time_diff', 'position', 'pace', 'up',
                        'body_weight', 'winner', 'prize', 'new_flg',
                        'win_1_flg', 'win_2_flg', 'win_3_flg',
                        'not_win_flg', 'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg'
                    ]:
                        setattr(existing_record, field, row.get(field, None))
                    
                    existing_record.updated_at = timezone.now()
                    existing_record.updated_user = user_name
                    existing_record.save()

            else:
                # 新規作成
                HorseData.objects.create(
                    horse_id=row['horse_id'],
                    horse_name=row['horse_name'],
                    race_date=row['race_date'],
                    race_place=row['race_place'],
                    weather=row['weather'],
                    race_name=row['race_name'],
                    horse_number=row['horse_number'],
                    count=row['count'],
                    frame=row['frame'],
                    odds=row['odds'],
                    popularity=row['popularity'],
                    rank=row['rank'],
                    jockey=row['jockey'],
                    weight=row['weight'],
                    distance=row['distance'],
                    track_condition=row['track_condition'],
                    time=row['time'],
                    time_diff=row['time_diff'],
                    position=row['position'],
                    pace=row['pace'],
                    up=row['up'],
                    body_weight=row['body_weight'],
                    winner=row['winner'],
                    prize=row['prize'],
                    new_flg=row['new_flg'],
                    win_1_flg=row['win_1_flg'],
                    win_2_flg=row['win_2_flg'],
                    win_3_flg=row['win_3_flg'],
                    not_win_flg=row['not_win_flg'],
                    g3_flg=row['g3_flg'],
                    g2_flg=row['g2_flg'],
                    g1_flg=row['g1_flg'],
                    l_flg=row['l_flg'],
                    op_flg=row['op_flg'],
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                    created_user=user_name,
                    updated_user=user_name
                )

        except Exception as e:
            print(f"エラーが発生しました (行 {i}{field}): {e}")

# endregion

def insert_jockey_db(jockey_df, user_name):
    """
    取得したデータフレームを元にhorse_infoに追加・更新

    Parameters:
    ----------
    horse_df : DataFrame
        馬データ情報
    user_name : str
        ログインユーザー
    """
    # region "取得したデータフレームを元にhorse_infoに追加・更新"
    # print(jockey_df.columns)
    for i, row in jockey_df.iterrows():
        try:
            # 既存のレコードを取得
            existing_record = JockeyData.objects.filter(
                jockey_id=row['jockey_id'], race_date=row['race_date'], race=row['race']
            ).first()

            if existing_record:
                
                # 更新処理: データが異なる場合のみ更新
                is_different = any(
                    getattr(existing_record, field) != row.get(field, None)
                    for field in [
                        'race_place', 'weather', 'race_name', 'horse_number',
                        'count', 'frame', 'odds', 'popularity', 'rank',
                        'horse', 'weight', 'distance', 'track_condition',
                        'time', 'time_diff', 'position', 'pace', 'up',
                        'body_weight', 'winner', 'prize', 'new_flg',
                        'win_1_flg', 'win_2_flg', 'win_3_flg',
                        'not_win_flg', 'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg'
                    ]
                )

                if is_different:
                    # 差分があればフィールドを更新
                    for field in [
                        'race_place', 'weather', 'race_name', 'horse_number',
                        'count', 'frame', 'odds', 'popularity', 'rank',
                        'horse', 'weight', 'distance', 'track_condition',
                        'time', 'time_diff', 'position', 'pace', 'up',
                        'body_weight', 'winner', 'prize', 'new_flg',
                        'win_1_flg', 'win_2_flg', 'win_3_flg',
                        'not_win_flg', 'g3_flg', 'g2_flg', 'g1_flg', 'l_flg', 'op_flg'
                    ]:
                        setattr(existing_record, field, row.get(field, None))
                    
                    existing_record.updated_at = timezone.now()
                    existing_record.updated_user = user_name
                    existing_record.save()
                    flg = True

            else:
                # 新規作成
                JockeyData.objects.create(
                    jockey_id=row['jockey_id'],
                    jockey_name=row['jockey_name'],
                    race_date=row['race_date'],
                    race_place=row['race_place'],
                    weather=row['weather'],
                    race=row['race'],
                    race_name=row['race_name'],
                    horse_number=row['horse_number'],
                    count=row['count'],
                    frame=row['frame'],
                    odds=row['odds'],
                    popularity=row['popularity'],
                    rank=row['rank'],
                    horse=row['horse'],
                    weight=row['weight'],
                    distance=row['distance'],
                    track_condition=row['track_condition'],
                    time=row['time'],
                    time_diff=row['time_diff'],
                    position=row['position'],
                    pace=row['pace'],
                    up=row['up'],
                    body_weight=row['body_weight'],
                    winner=row['winner'],
                    prize=row['prize'],
                    new_flg=row['new_flg'],
                    win_1_flg=row['win_1_flg'],
                    win_2_flg=row['win_2_flg'],
                    win_3_flg=row['win_3_flg'],
                    not_win_flg=row['not_win_flg'],
                    g3_flg=row['g3_flg'],
                    g2_flg=row['g2_flg'],
                    g1_flg=row['g1_flg'],
                    l_flg=row['l_flg'],
                    op_flg=row['op_flg'],
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                    created_user=user_name,
                    updated_user=user_name
                )
                flg = False

        except Exception as e:
            flg = False
            print(e)

    return flg

def insert_result_db(result_df, user_name):
    """
    結果データをresult_dataに追加・更新
    
    Parameters:
    ----------
    result_df : DataFrame
        結果データ
    user_name : str
        ログインユーザー名

    """ 
    # region "結果データをresult_dataに追加・更新"
    
    for i, row in result_df.iterrows():
        # race_id と horse_number に基づいて既存のレコードを検索
        existing_record = ResultData.objects.filter(
            race_id=row['race_id'],
            horse_number=row['horse_number']
        ).first()

        if existing_record:
            # 既存レコードが見つかった場合、差分があるかをチェック
            is_different = any(
                getattr(existing_record, field) != row[field]
                for field in [
                    'horse_name', 'rank', 'race_time', 'corner_order', 'race_date',
                    'positions', 'positions_tie', 'pay1', 'pay1_tie', 'pay123_1', 'pay123_2', 
                    'pay123_3', 'pay123_tie' ,'pay123_12_1' ,'pay123_12_2' ,'pay123_12_3' ,'pay123_12_4_tie',
                    'pay123_12_5_tie' ,'pay12_21' ,'pay12_21_tie' ,'pay12_12' ,'pay12_12_tie',
                    'pay123_321' ,'pay123_321_tie' ,'pay123_123' ,'pay123_123_tie'
                ]
            )

            # 差分があれば更新
            if is_different:
                for field in [
                    'horse_name', 'rank', 'race_time', 'corner_order', 'race_date',
                    'positions', 'positions_tie', 'pay1', 'pay1_tie', 'pay123_1', 'pay123_2', 
                    'pay123_3', 'pay123_tie' ,'pay123_12_1' ,'pay123_12_2' ,'pay123_12_3' ,'pay123_12_4_tie',
                    'pay123_12_5_tie' ,'pay12_21' ,'pay12_21_tie' ,'pay12_12' ,'pay12_12_tie',
                    'pay123_321' ,'pay123_321_tie' ,'pay123_123' ,'pay123_123_tie'
                ]:
                    setattr(existing_record, field, row[field])

                # 更新日時と更新者を設定
                existing_record.updated_at = timezone.now()
                existing_record.updated_user = user_name
                existing_record.save()
        else:
            # 既存レコードがない場合は新規追加
            ResultData.objects.create(
                race_id=row['race_id'],
                horse_number=row['horse_number'],
                horse_name=row['horse_name'],
                rank=row['rank'],
                race_time=row['race_time'],
                corner_order=row['corner_order'],
                race_date=row['race_date'],
                positions=row['positions'],
                positions_tie=row['positions_tie'],
                pay1=row['pay1'],
                pay1_tie=row['pay1_tie'],
                pay123_1=row['pay123_1'],
                pay123_2=row['pay123_2'],
                pay123_3=row['pay123_3'],
                pay123_tie=row['pay123_tie'],
                pay123_12_1=row['pay123_12_1'],
                pay123_12_2=row['pay123_12_2'],
                pay123_12_3=row['pay123_12_3'],
                pay123_12_4_tie=row['pay123_12_4_tie'],
                pay123_12_5_tie=row['pay123_12_5_tie'],
                pay12_21=row['pay12_21'],
                pay12_21_tie=row['pay12_21_tie'],
                pay12_12=row['pay12_12'],
                pay12_12_tie=row['pay12_12_tie'],
                pay123_321=row['pay123_321'],
                pay123_321_tie=row['pay123_321_tie'],
                pay123_123=row['pay123_123'],
                pay123_123_tie=row['pay123_123_tie'],
                created_at=timezone.now(),
                updated_at=timezone.now(),
                created_user=user_name,
                updated_user=user_name
            )
# endregion

def insert_final_base_info():
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO
                T_FINAL_BASE_INFO (
                    "RACE_ID",
                    "TODAY_RACE_DATE",
                    "TODAY_RACE_NO",
                    "PLACE_ID",
                    "PLACE_NAME",
                    "HORSE_ID",
                    "HORSE",
                    "FRAME_NUMBER",
                    "HORSE_NUMBER",
                    "SEX",
                    "AGE",
                    "WEIGHT",
                    "BODY_WEIGHT",
                    "JOCKEY_ID",
                    "JOCKEY",
                    "WEIGHT_4KG_CUT_FLG",
                    "WEIGHT_3KG_CUT_FLG",
                    "WEIGHT_2KG_CUT_FLG",
                    "WEIGHT_1KG_CUT_FLG",
                    "WOMEN_WEIGHT_2KG_CUT_FLG",
                    "STABLE_NAME",
                    "ODDS",
                    "POPULARITY",
                    "NEW_FLG",
                    "G1_FLG",
                    "G2_FLG",
                    "G3_FLG",
                    "L_FLG",
                    "NOT_WIN_FLG",
                    "OP_FLG",
                    "WIN_1_FLG",
                    "WIN_2_FLG",
                    "WIN_3_FLG",
                    "IS_WIN5"
                )
            SELECT
                RACE_ID,
                TODAY_RACE_DATE,
                TODAY_RACE_NO,
                PLACE_ID,
                PLACE_NAME,
                HORSE_ID,
                HORSE_NAME,
                FRAME_NUMBER,
                HORSE_NUMBER,
                SEX,
                AGE,
                WEIGHT,
                BODY_WEIGHT,
                JOCKEY_ID,
                JOCKEY_NAME,
                "WEIGHT_4KG_CUT_FLG",
                "WEIGHT_3KG_CUT_FLG",
                "WEIGHT_2KG_CUT_FLG",
                "WEIGHT_1KG_CUT_FLG",
                "WOMEN_WEIGHT_2KG_CUT_FLG",
                STABLE_NAME,
                ODDS,
                POPULARITY,
                NEW_FLG,
                G1_FLG,
                G2_FLG,
                G3_FLG,
                L_FLG,
                NOT_WIN_FLG,
                OP_FLG,
                WIN_1_FLG,
                WIN_2_FLG,
                WIN_3_FLG,
                IS_WIN5
            FROM
                V_BASE_INFO
            ON CONFLICT ("RACE_ID", "HORSE_ID", "JOCKEY_ID") DO NOTHING;
        """)

def insert_final_horse_info():
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO
                T_FINAL_HORSE_INFO (
                    "TODAY_RACE_DATE",
                    "RACE_DATE",
                    "RACE_NAME",
                    "TRACK_CONDITION",
                    "WEATHER",
                    "PLACE_ID",
                    "PLACE_NAME",
                    "COUNT",
                    "FIELD",
                    "DISTANCE",
                    "HORSE_ID",
                    "BODY_WEIGHT",
                    "FRAME_NUMBER",
                    "HORSE_NUMBER",
                    "JOCKEY",
                    "RANK",
                    "TIME",
                    "TIME_DIFF",
                    "TIME_UP",
                    "PACE_1",
                    "PACE_2",
                    "POSITION_1",
                    "POSITION_2",
                    "POSITION_3",
                    "POSITION_4",
                    "ODDS",
                    "POPULARITY",
                    "WINNER",
                    "PRIZE",
                    "NEW_FLG",
                    "G1_FLG",
                    "G2_FLG",
                    "G3_FLG",
                    "L_FLG",
                    "NOT_WIN_FLG",
                    "OP_FLG",
                    "WIN_1_FLG",
                    "WIN_2_FLG",
                    "WIN_3_FLG",
                    "GR_ID"
                )
            SELECT
                *
            FROM
                (
                    SELECT
                        SUB."TODAY_RACE_DATE",
                        SUB.HISTORY_RACE_DATE,
                        SUB.RACE_NAME,
                        SUB.TRACK_CONDITION,
                        SUB.WEATHER,
                        SUB.PLACE_ID,
                        SUB.PLACE_NAME,
                        SUB.COUNT,
                        SUB.FIELD,
                        SUB.DISTANCE,
                        SUB.HORSE_ID,
                        SUB.BODY_WEIGHT,
                        SUB.FRAME_NUMBER,
                        SUB.HORSE_NUMBER,
                        SUB.JOCKEY,
                        SUB.RANK,
                        SUB.TIME,
                        SUB.TIME_DIFF,
                        SUB.TIME_UP,
                        SUB.PACE_1,
                        SUB.PACE_2,
                        SUB.POSITION_1,
                        SUB.POSITION_2,
                        SUB.POSITION_3,
                        SUB.POSITION_4,
                        SUB.ODDS,
                        SUB.POPULARITY,
                        SUB.WINNER,
                        SUB.PRIZE,
                        SUB.NEW_FLG,
                        SUB.G1_FLG,
                        SUB.G2_FLG,
                        SUB.G3_FLG,
                        SUB.L_FLG,
                        SUB.NOT_WIN_FLG,
                        SUB.OP_FLG,
                        SUB.WIN_1_FLG,
                        SUB.WIN_2_FLG,
                        SUB.WIN_3_FLG,
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                SUB.HORSE_ID,
                                SUB."TODAY_RACE_DATE"
                            ORDER BY
                                SUB.HISTORY_RACE_DATE DESC
                        ) AS GR_ID
                    FROM
                        (
                            SELECT
                                VH.*,
                                TB."TODAY_RACE_DATE"
                            FROM
                                V_HORSE_INFO VH
                                INNER JOIN T_FINAL_BASE_INFO TB ON VH.HORSE_ID = TB."HORSE_ID"
                            WHERE
                                VH.HISTORY_RACE_DATE < TB."TODAY_RACE_DATE"
                        ) SUB
                ) SUB1
            WHERE
                SUB1.GR_ID <= 10
            ON CONFLICT (
                "TODAY_RACE_DATE",
                "RACE_DATE",
                "HORSE_ID",
                "JOCKEY"
            ) DO NOTHING;
        """)

def insert_final_jockey_info():
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO
                T_FINAL_JOCKEY_INFO (
                    "TODAY_RACE_DATE",
                    "TODAY_RACE_NO",
                    "RACE_DATE",
                    "RACE_NO",
                    "RACE_NAME",
                    "TRACK_CONDITION",
                    "WEATHER",
                    "PLACE_ID",
                    "PLACE_NAME",
                    "COUNT",
                    "FIELD",
                    "DISTANCE",
                    "JOCKEY_ID",
                    "BODY_WEIGHT",
                    "WEIGHT",
                    "FRAME_NUMBER",
                    "HORSE_NUMBER",
                    "HORSE",
                    "RANK",
                    "TIME",
                    "TIME_DIFF",
                    "TIME_UP",
                    "PACE_1",
                    "PACE_2",
                    "POSITION_1",
                    "POSITION_2",
                    "POSITION_3",
                    "POSITION_4",
                    "ODDS",
                    "POPULARITY",
                    "WINNER",
                    "PRIZE",
                    "WEIGHT_4KG_CUT_FLG",
                    "WEIGHT_3KG_CUT_FLG",
                    "WEIGHT_2KG_CUT_FLG",
                    "WEIGHT_1KG_CUT_FLG",
                    "WOMEN_WEIGHT_2KG_CUT_FLG",
                    "NEW_FLG",
                    "G1_FLG",
                    "G2_FLG",
                    "G3_FLG",
                    "L_FLG",
                    "NOT_WIN_FLG",
                    "OP_FLG",
                    "WIN_1_FLG",
                    "WIN_2_FLG",
                    "WIN_3_FLG",
                    "GR_ID"
                )
            SELECT
                SUB1.*
            FROM
                (
                    SELECT
                        SUB."TODAY_RACE_DATE",
                        SUB."TODAY_RACE_NO",
                        SUB.HISTORY_RACE_DATE,
                        SUB.HISTORY_RACE_NO,
                        SUB.RACE_NAME,
                        SUB.TRACK_CONDITION,
                        SUB.WEATHER,
                        SUB.PLACE_ID,
                        SUB.PLACE_NAME,
                        SUB.COUNT,
                        SUB.FIELD,
                        SUB.DISTANCE,
                        SUB.JOCKEY_ID,
                        SUB.BODY_WEIGHT,
                        SUB.WEIGHT,
                        SUB.FRAME_NUMBER,
                        SUB.HORSE_NUMBER,
                        SUB.HORSE,
                        SUB.RANK,
                        SUB.TIME,
                        SUB.TIME_DIFF,
                        SUB.TIME_UP,
                        SUB.PACE_1,
                        SUB.PACE_2,
                        SUB.POSITION_1,
                        SUB.POSITION_2,
                        SUB.POSITION_3,
                        SUB.POSITION_4,
                        SUB.ODDS,
                        SUB.POPULARITY,
                        SUB.WINNER,
                        SUB.PRIZE,
                        SUB."WEIGHT_4KG_CUT_FLG",
                        SUB."WEIGHT_3KG_CUT_FLG",
                        SUB."WEIGHT_2KG_CUT_FLG",
                        SUB."WEIGHT_1KG_CUT_FLG",
                        SUB."WOMEN_WEIGHT_2KG_CUT_FLG",
                        SUB.NEW_FLG,
                        SUB.G1_FLG,
                        SUB.G2_FLG,
                        SUB.G3_FLG,
                        SUB.L_FLG,
                        SUB.NOT_WIN_FLG,
                        SUB.OP_FLG,
                        SUB.WIN_1_FLG,
                        SUB.WIN_2_FLG,
                        SUB.WIN_3_FLG,
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                SUB.JOCKEY_ID,
                                SUB."TODAY_RACE_DATE",
                                SUB."TODAY_RACE_NO"
                            ORDER BY
                                SUB.HISTORY_RACE_DATE DESC,
                                SUB.HISTORY_RACE_NO
                        ) AS GR_ID
                    FROM
                        (
                            SELECT
                                TB."TODAY_RACE_DATE",
                                TB."TODAY_RACE_NO",
                                VJ.*
                            FROM
                                V_JOCKEY_INFO VJ
                                INNER JOIN T_FINAL_BASE_INFO TB ON VJ.JOCKEY_ID = TB."JOCKEY_ID"
                            WHERE
                                VJ.HISTORY_RACE_DATE < TB."TODAY_RACE_DATE"
                                OR (
                                    VJ.HISTORY_RACE_DATE = TB."TODAY_RACE_DATE"
                                    AND VJ.HISTORY_RACE_NO < TB."TODAY_RACE_NO"
                                )
                        ) SUB
                ) SUB1
            WHERE
                SUB1.GR_ID <= 10
            ON CONFLICT (
                "TODAY_RACE_DATE",
                "TODAY_RACE_NO",
                "RACE_DATE",
                "RACE_NO",
                "HORSE",
                "JOCKEY_ID"
            ) DO NOTHING;
        """)

def insert_final_result_info():
    with connection.cursor() as cursor:
        # v_result_info からデータを取得
        cursor.execute("""
            INSERT INTO
                T_FINAL_RESULT_INFO (
                    "RACE_ID",
                    "HORSE_NUMBER",
                    "RANK",
                    "RACE_TIME",
                    "CORNER_ORDER",
                    "POSITIONS",
                    "POSITIONS_TIE",
                    "PAY1",
                    "PAY1_TIE",
                    "PAY123_1",
                    "PAY123_2",
                    "PAY123_3",
                    "PAY123_TIE",
                    "PAY123_12_1",
                    "PAY123_12_2",
                    "PAY123_12_3",
                    "PAY123_12_4_TIE",
                    "PAY123_12_5_TIE",
                    "PAY12_21",
                    "PAY12_21_TIE",
                    "PAY12_12",
                    "PAY12_12_TIE",
                    "PAY123_321",
                    "PAY123_321_TIE",
                    "PAY123_123",
                    "PAY123_123_TIE"
                )
            SELECT
                RACE_ID,
                HORSE_NUMBER,
                RANK,
                RACE_TIME,
                CORNER_ORDER,
                POSITIONS,
                POSITIONS_TIE,
                PAY1,
                PAY1_TIE,
                PAY123_1,
                PAY123_2,
                PAY123_3,
                PAY123_TIE,
                PAY123_12_1,
                PAY123_12_2,
                PAY123_12_3,
                PAY123_12_4_TIE,
                PAY123_12_5_TIE,
                PAY12_21,
                PAY12_21_TIE,
                PAY12_12,
                PAY12_12_TIE,
                PAY123_321,
                PAY123_321_TIE,
                PAY123_123,
                PAY123_123_TIE
            FROM
                V_RESULT_INFO
            ON CONFLICT ("RACE_ID", "HORSE_NUMBER") DO NOTHING;
        """)

def insert_training_info():
    with connection.cursor() as cursor:
        # v_result_info からデータを取得
        cursor.execute("""
            INSERT INTO 
                T_TRAINING (
                    "RACE_ID_TODAY",
                    "RACE_DATE_TODAY",
                    "RACE_NO_TODAY",
                    "PLACE_ID_TODAY",
                    "PLACE_NAME_TODAY",
                    "HORSE_ID_TODAY",
                    "HORSE_TODAY",
                    "FRAME_NUMBER_TODAY",
                    "HORSE_NUMBER_TODAY",
                    "SEX_TODAY",
                    "AGE_TODAY",
                    "WEIGHT_TODAY",
                    "BODY_WEIGHT_TODAY",
                    "JOCKEY_ID_TODAY",
                    "JOCKEY_TODAY",
                    "WEIGHT_4KG_CUT_FLG_TODAY",
                    "WEIGHT_3KG_CUT_FLG_TODAY",
                    "WEIGHT_2KG_CUT_FLG_TODAY",
                    "WEIGHT_1KG_CUT_FLG_TODAY",
                    "WOMEN_WEIGHT_2KG_CUT_FLG_TODAY",
                    "STABLE_NAME_TODAY",
                    "ODDS_TODAY",
                    "POPULARITY_TODAY",
                    "NEW_FLG_TODAY",
                    "G1_FLG_TODAY",
                    "G2_FLG_TODAY",
                    "G3_FLG_TODAY",
                    "L_FLG_TODAY",
                    "NOT_WIN_FLG_TODAY",
                    "OP_FLG_TODAY",
                    "WIN_1_FLG_TODAY",
                    "WIN_2_FLG_TODAY",
                    "WIN_3_FLG_TODAY",
                    "IS_WIN5_TODAY",	
                    "RACE_DATE_H_H_HISTORY1",
                    "RACE_NAME_H_HISTORY1",
                    "PLACE_ID_H_HISTORY1",
                    "PLACE_NAME_H_HISTORY1",
                    "TRACK_CONDITION_H_HISTORY1",
                    "WEATHER_H_HISTORY1",
                    "COUNT_H_HISTORY1",
                    "FIELD_H_HISTORY1",
                    "DISTANCE_H_HISTORY1",
                    "FRAME_NUMBER_H_HISTORY1",
                    "HORSE_NUMBER_H_HISTORY1",
                    "BODY_WEIGHT_H_HISTORY1",
                    "JOCKEY_H_HISTORY1",
                    "ODDS_H_HISTORY1",
                    "POPULARITY_H_HISTORY1",
                    "RANK_H_HISTORY1",
                    "TIME_H_HISTORY1",
                    "TIME_DIFF_H_HISTORY1",
                    "TIME_UP_H_HISTORY1",
                    "PACE_1_H_HISTORY1",
                    "PACE_2_H_HISTORY1",
                    "POSITION_1_H_HISTORY1",
                    "POSITION_2_H_HISTORY1",
                    "POSITION_3_H_HISTORY1",
                    "POSITION_4_H_HISTORY1",
                    "WINNER_H_HISTORY1",
                    "PRIZE_H_HISTORY1",
                    "NEW_FLG_H_HISTORY1",
                    "G1_FLG_H_HISTORY1",
                    "G2_FLG_H_HISTORY1",
                    "G3_FLG_H_HISTORY1",
                    "L_FLG_H_HISTORY1",
                    "NOT_WIN_FLG_H_HISTORY1",
                    "OP_FLG_H_HISTORY1",
                    "WIN_1_FLG_H_HISTORY1",
                    "WIN_2_FLG_H_HISTORY1",
                    "WIN_3_FLG_H_HISTORY1",
                    "RACE_DATE_H_HISTORY2",
                    "RACE_NAME_H_HISTORY2",
                    "PLACE_ID_H_HISTORY2",
                    "PLACE_NAME_H_HISTORY2",
                    "TRACK_CONDITION_H_HISTORY2",
                    "WEATHER_H_HISTORY2",
                    "COUNT_H_HISTORY2",
                    "FIELD_H_HISTORY2",
                    "DISTANCE_H_HISTORY2",
                    "FRAME_NUMBER_H_HISTORY2",
                    "HORSE_NUMBER_H_HISTORY2",
                    "BODY_WEIGHT_H_HISTORY2",
                    "JOCKEY_H_HISTORY2",
                    "ODDS_H_HISTORY2",
                    "POPULARITY_H_HISTORY2",
                    "RANK_H_HISTORY2",
                    "TIME_H_HISTORY2",
                    "TIME_DIFF_H_HISTORY2",
                    "TIME_UP_H_HISTORY2",
                    "PACE_1_H_HISTORY2",
                    "PACE_2_H_HISTORY2",
                    "POSITION_1_H_HISTORY2",
                    "POSITION_2_H_HISTORY2",
                    "POSITION_3_H_HISTORY2",
                    "POSITION_4_H_HISTORY2",
                    "WINNER_H_HISTORY2",
                    "PRIZE_H_HISTORY2",
                    "NEW_FLG_H_HISTORY2",
                    "G1_FLG_H_HISTORY2",
                    "G2_FLG_H_HISTORY2",
                    "G3_FLG_H_HISTORY2",
                    "L_FLG_H_HISTORY2",
                    "NOT_WIN_FLG_H_HISTORY2",
                    "OP_FLG_H_HISTORY2",
                    "WIN_1_FLG_H_HISTORY2",
                    "WIN_2_FLG_H_HISTORY2",
                    "WIN_3_FLG_H_HISTORY2",
                    "RACE_DATE_H_HISTORY3",
                    "RACE_NAME_H_HISTORY3",
                    "PLACE_ID_H_HISTORY3",
                    "PLACE_NAME_H_HISTORY3",
                    "TRACK_CONDITION_H_HISTORY3",
                    "WEATHER_H_HISTORY3",
                    "COUNT_H_HISTORY3",
                    "FIELD_H_HISTORY3",
                    "DISTANCE_H_HISTORY3",
                    "FRAME_NUMBER_H_HISTORY3",
                    "HORSE_NUMBER_H_HISTORY3",
                    "BODY_WEIGHT_H_HISTORY3",
                    "JOCKEY_H_HISTORY3",
                    "ODDS_H_HISTORY3",
                    "POPULARITY_H_HISTORY3",
                    "RANK_H_HISTORY3",
                    "TIME_H_HISTORY3",
                    "TIME_DIFF_H_HISTORY3",
                    "TIME_UP_H_HISTORY3",
                    "PACE_1_H_HISTORY3",
                    "PACE_2_H_HISTORY3",
                    "POSITION_1_H_HISTORY3",
                    "POSITION_2_H_HISTORY3",
                    "POSITION_3_H_HISTORY3",
                    "POSITION_4_H_HISTORY3",
                    "WINNER_H_HISTORY3",
                    "PRIZE_H_HISTORY3",
                    "NEW_FLG_H_HISTORY3",
                    "G1_FLG_H_HISTORY3",
                    "G2_FLG_H_HISTORY3",
                    "G3_FLG_H_HISTORY3",
                    "L_FLG_H_HISTORY3",
                    "NOT_WIN_FLG_H_HISTORY3",
                    "OP_FLG_H_HISTORY3",
                    "WIN_1_FLG_H_HISTORY3",
                    "WIN_2_FLG_H_HISTORY3",
                    "WIN_3_FLG_H_HISTORY3",
                    "RACE_DATE_J_HISTORY1",
                    "RACE_NO_J_HISTORY1",
                    "RACE_NAME_J_HISTORY1",
                    "TRACK_CONDITION_J_HISTORY1",
                    "WEATHER_J_HISTORY1",
                    "PLACE_ID_J_HISTORY1",
                    "PLACE_NAME_J_HISTORY1",
                    "COUNT_J_HISTORY1",
                    "FIELD_J_HISTORY1",
                    "DISTANCE_J_HISTORY1",
                    "BODY_WEIGHT_J_HISTORY1",
                    "WEIGHT_J_HISTORY1",
                    "FRAME_NUMBER_J_HISTORY1",
                    "HORSE_NUMBER_J_HISTORY1",
                    "HORSE_J_HISTORY1",
                    "RANK_J_HISTORY1",
                    "TIME_J_HISTORY1",
                    "TIME_DIFF_J_HISTORY1",
                    "TIME_UP_J_HISTORY1",
                    "PACE_1_J_HISTORY1",
                    "PACE_2_J_HISTORY1",
                    "POSITION_1_J_HISTORY1",
                    "POSITION_2_J_HISTORY1",
                    "POSITION_3_J_HISTORY1",
                    "POSITION_4_J_HISTORY1",
                    "ODDS_J_HISTORY1",
                    "POPULARITY_J_HISTORY1",
                    "WINNER_J_HISTORY1",
                    "PRIZE_J_HISTORY1",
                    "WEIGHT_4KG_CUT_FLG_J_HISTORY1",
                    "WEIGHT_3KG_CUT_FLG_J_HISTORY1",
                    "WEIGHT_2KG_CUT_FLG_J_HISTORY1",
                    "WEIGHT_1KG_CUT_FLG_J_HISTORY1",
                    "WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY1",
                    "NEW_FLG_J_HISTORY1",
                    "G1_FLG_J_HISTORY1",
                    "G2_FLG_J_HISTORY1",
                    "G3_FLG_J_HISTORY1",
                    "L_FLG_J_HISTORY1",
                    "NOT_WIN_FLG_J_HISTORY1",
                    "OP_FLG_J_HISTORY1",
                    "WIN_1_FLG_J_HISTORY1",
                    "WIN_2_FLG_J_HISTORY1",
                    "WIN_3_FLG_J_HISTORY1",
                    "RACE_DATE_J_HISTORY2",
                    "RACE_NO_J_HISTORY2",
                    "RACE_NAME_J_HISTORY2",
                    "TRACK_CONDITION_J_HISTORY2",
                    "WEATHER_J_HISTORY2",
                    "PLACE_ID_J_HISTORY2",
                    "PLACE_NAME_J_HISTORY2",
                    "COUNT_J_HISTORY2",
                    "FIELD_J_HISTORY2",
                    "DISTANCE_J_HISTORY2",
                    "BODY_WEIGHT_J_HISTORY2",
                    "WEIGHT_J_HISTORY2",
                    "FRAME_NUMBER_J_HISTORY2",
                    "HORSE_NUMBER_J_HISTORY2",
                    "HORSE_J_HISTORY2",
                    "RANK_J_HISTORY2",
                    "TIME_J_HISTORY2",
                    "TIME_DIFF_J_HISTORY2",
                    "TIME_UP_J_HISTORY2",
                    "PACE_1_J_HISTORY2",
                    "PACE_2_J_HISTORY2",
                    "POSITION_1_J_HISTORY2",
                    "POSITION_2_J_HISTORY2",
                    "POSITION_3_J_HISTORY2",
                    "POSITION_4_J_HISTORY2",
                    "ODDS_J_HISTORY2",
                    "POPULARITY_J_HISTORY2",
                    "WINNER_J_HISTORY2",
                    "PRIZE_J_HISTORY2",
                    "WEIGHT_4KG_CUT_FLG_J_HISTORY2",
                    "WEIGHT_3KG_CUT_FLG_J_HISTORY2",
                    "WEIGHT_2KG_CUT_FLG_J_HISTORY2",
                    "WEIGHT_1KG_CUT_FLG_J_HISTORY2",
                    "WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY2",
                    "NEW_FLG_J_HISTORY2",
                    "G1_FLG_J_HISTORY2",
                    "G2_FLG_J_HISTORY2",
                    "G3_FLG_J_HISTORY2",
                    "L_FLG_J_HISTORY2",
                    "NOT_WIN_FLG_J_HISTORY2",
                    "OP_FLG_J_HISTORY2",
                    "WIN_1_FLG_J_HISTORY2",
                    "WIN_2_FLG_J_HISTORY2",
                    "WIN_3_FLG_J_HISTORY2",
                    "RACE_DATE_J_HISTORY3",
                    "RACE_NO_J_HISTORY3",
                    "RACE_NAME_J_HISTORY3",
                    "TRACK_CONDITION_J_HISTORY3",
                    "WEATHER_J_HISTORY3",
                    "PLACE_ID_J_HISTORY3",
                    "PLACE_NAME_J_HISTORY3",
                    "COUNT_J_HISTORY3",
                    "FIELD_J_HISTORY3",
                    "DISTANCE_J_HISTORY3",
                    "BODY_WEIGHT_J_HISTORY3",
                    "WEIGHT_J_HISTORY3",
                    "FRAME_NUMBER_J_HISTORY3",
                    "HORSE_NUMBER_J_HISTORY3",
                    "HORSE_J_HISTORY3",
                    "RANK_J_HISTORY3",
                    "TIME_J_HISTORY3",
                    "TIME_DIFF_J_HISTORY3",
                    "TIME_UP_J_HISTORY3",
                    "PACE_1_J_HISTORY3",
                    "PACE_2_J_HISTORY3",
                    "POSITION_1_J_HISTORY3",
                    "POSITION_2_J_HISTORY3",
                    "POSITION_3_J_HISTORY3",
                    "POSITION_4_J_HISTORY3",
                    "ODDS_J_HISTORY3",
                    "POPULARITY_J_HISTORY3",
                    "WINNER_J_HISTORY3",
                    "PRIZE_J_HISTORY3",
                    "WEIGHT_4KG_CUT_FLG_J_HISTORY3",
                    "WEIGHT_3KG_CUT_FLG_J_HISTORY3",
                    "WEIGHT_2KG_CUT_FLG_J_HISTORY3",
                    "WEIGHT_1KG_CUT_FLG_J_HISTORY3",
                    "WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY3",
                    "NEW_FLG_J_HISTORY3",
                    "G1_FLG_J_HISTORY3",
                    "G2_FLG_J_HISTORY3",
                    "G3_FLG_J_HISTORY3",
                    "L_FLG_J_HISTORY3",
                    "NOT_WIN_FLG_J_HISTORY3",
                    "OP_FLG_J_HISTORY3",
                    "WIN_1_FLG_J_HISTORY3",
                    "WIN_2_FLG_J_HISTORY3",
                    "WIN_3_FLG_J_HISTORY3",
                    "RANK",
                    "RACE_TIME",
                    "CORNER_ORDER",
                    "POSITIONS",
                    "POSITIONS_TIE",
                    "PAY1",
                    "PAY1_TIE",
                    "PAY123_1",
                    "PAY123_2",
                    "PAY123_3",
                    "PAY123_TIE",
                    "PAY123_12_1",
                    "PAY123_12_2",
                    "PAY123_12_3",
                    "PAY123_12_4_TIE",
                    "PAY123_12_5_TIE",
                    "PAY12_21",
                    "PAY12_21_TIE",
                    "PAY12_12",
                    "PAY12_12_TIE",
                    "PAY123_321",
                    "PAY123_321_TIE",
                    "PAY123_123",
                    "PAY123_123_TIE"
                )
                SELECT
                    VB_MAIN."RACE_ID" AS RACE_ID_TODAY,
                    VB_MAIN."TODAY_RACE_DATE" AS RACE_DATE_TODAY,
                    VB_MAIN."TODAY_RACE_NO" AS RACE_NO_TODAY,
                    VB_MAIN."PLACE_ID" AS PLACE_ID_TODAY,
                    VB_MAIN."PLACE_NAME" AS PLACE_NAME_TODAY,
                    VB_MAIN."HORSE_ID" AS HORSE_ID_TODAY,
                    VB_MAIN."HORSE" AS HORSE_TODAY,
                    VB_MAIN."FRAME_NUMBER" AS FRAME_NUMBER_TODAY,
                    VB_MAIN."HORSE_NUMBER" AS HORSE_NUMBER_TODAY,
                    VB_MAIN."SEX" AS SEX_TODAY,
                    VB_MAIN."AGE" AS AGE_TODAY,
                    VB_MAIN."WEIGHT" AS WEIGHT_TODAY,
                    VB_MAIN."BODY_WEIGHT" AS BODY_WEIGHT_TODAY,
                    VB_MAIN."JOCKEY_ID" AS JOCKEY_ID_TODAY,
                    VB_MAIN."JOCKEY" AS JOCKEY_TODAY,
                    VB_MAIN."WEIGHT_4KG_CUT_FLG" AS WEIGHT_4KG_CUT_FLG_TODAY,
                    VB_MAIN."WEIGHT_3KG_CUT_FLG" AS WEIGHT_3KG_CUT_FLG_TODAY,
                    VB_MAIN."WEIGHT_2KG_CUT_FLG" AS WEIGHT_2KG_CUT_FLG_TODAY,
                    VB_MAIN."WEIGHT_1KG_CUT_FLG" AS WEIGHT_1KG_CUT_FLG_TODAY,
                    VB_MAIN."WOMEN_WEIGHT_2KG_CUT_FLG" AS WOMEN_WEIGHT_2KG_CUT_FLG_TODAY,
                    VB_MAIN."STABLE_NAME" AS STABLE_NAME_TODAY,
                    VB_MAIN."ODDS" AS ODDS_TODAY,
                    VB_MAIN."POPULARITY" AS POPULARITY_TODAY,
                    VB_MAIN."NEW_FLG" AS NEW_FLG_TODAY,
                    VB_MAIN."G1_FLG" AS G1_FLG_TODAY,
                    VB_MAIN."G2_FLG" AS G2_FLG_TODAY,
                    VB_MAIN."G3_FLG" AS G3_FLG_TODAY,
                    VB_MAIN."L_FLG" AS L_FLG_TODAY,
                    VB_MAIN."NOT_WIN_FLG" AS NOT_WIN_FLG_TODAY,
                    VB_MAIN."OP_FLG" AS OP_FLG_TODAY,
                    VB_MAIN."WIN_1_FLG" AS WIN_1_FLG_TODAY,
                    VB_MAIN."WIN_2_FLG" AS WIN_2_FLG_TODAY,
                    VB_MAIN."WIN_3_FLG" AS WIN_3_FLG_TODAY,
                    VB_MAIN."IS_WIN5" AS IS_WIN5_TODAY,
                    VH1."RACE_DATE" AS RACE_DATE_H_HISTORY1,
                    VH1."RACE_NAME" AS RACE_NAME_H_HISTORY1,
                    VH1."PLACE_ID" AS PLACE_ID_H_HISTORY1,
                    VH1."PLACE_NAME" AS PLACE_NAME_H_HISTORY1,
                    VH1."TRACK_CONDITION" AS TRACK_CONDITION_H_HISTORY1,
                    VH1."WEATHER" AS WEATHER_H_HISTORY1,
                    VH1."COUNT" AS COUNT_H_HISTORY1,
                    VH1."FIELD" AS FIELD_H_HISTORY1,
                    VH1."DISTANCE" AS DISTANCE_H_HISTORY1,
                    VH1."FRAME_NUMBER" AS FRAME_NUMBER_H_HISTORY1,
                    VH1."HORSE_NUMBER" AS HORSE_NUMBER_H_HISTORY1,
                    VH1."BODY_WEIGHT" AS BODY_WEIGHT_H_HISTORY1,
                    VH1."JOCKEY" AS JOCKEY_H_HISTORY1,
                    VH1."ODDS" AS ODDS_H_HISTORY1,
                    VH1."POPULARITY" AS POPULARITY_H_HISTORY1,
                    VH1."RANK" AS RANK_H_HISTORY1,
                    VH1."TIME" AS TIME_H_HISTORY1,
                    VH1."TIME_DIFF" AS TIME_DIFF_H_HISTORY1,
                    VH1."TIME_UP" AS TIME_UP_H_HISTORY1,
                    VH1."PACE_1" AS PACE_1_H_HISTORY1,
                    VH1."PACE_2" AS PACE_2_H_HISTORY1,
                    VH1."POSITION_1" AS POSITION_1_H_HISTORY1,
                    VH1."POSITION_2" AS POSITION_2_H_HISTORY1,
                    VH1."POSITION_3" AS POSITION_3_H_HISTORY1,
                    VH1."POSITION_4" AS POSITION_4_H_HISTORY1,
                    VH1."WINNER" AS WINNER_H_HISTORY1,
                    VH1."PRIZE" AS PRIZE_H_HISTORY1,
                    COALESCE(VH1."NEW_FLG", false) AS NEW_FLG_H_HISTORY1,
                    COALESCE(VH1."G1_FLG", false) AS G1_FLG_H_HISTORY1,
                    COALESCE(VH1."G2_FLG", false) AS G2_FLG_H_HISTORY1,
                    COALESCE(VH1."G3_FLG", false) AS G3_FLG_H_HISTORY1,
                    COALESCE(VH1."L_FLG", false) AS L_FLG_H_HISTORY1,
                    COALESCE(VH1."NOT_WIN_FLG", false) AS NOT_WIN_FLG_H_HISTORY1,
                    COALESCE(VH1."OP_FLG", false) AS OP_FLG_H_HISTORY1,
                    COALESCE(VH1."WIN_1_FLG", false) AS WIN_1_FLG_H_HISTORY1,
                    COALESCE(VH1."WIN_2_FLG", false) AS WIN_2_FLG_H_HISTORY1,
                    COALESCE(VH1."WIN_3_FLG", false) AS WIN_3_FLG_H_HISTORY1,
                    VH2."RACE_DATE" AS RACE_DATE_H_HISTORY2,
                    VH2."RACE_NAME" AS RACE_NAME_H_HISTORY2,
                    VH2."PLACE_ID" AS PLACE_ID_H_HISTORY2,
                    VH2."PLACE_NAME" AS PLACE_NAME_H_HISTORY2,
                    VH2."TRACK_CONDITION" AS TRACK_CONDITION_H_HISTORY2,
                    VH2."WEATHER" AS WEATHER_H_HISTORY2,
                    VH2."COUNT" AS COUNT_H_HISTORY2,
                    VH2."FIELD" AS FIELD_H_HISTORY2,
                    VH2."DISTANCE" AS DISTANCE_H_HISTORY2,
                    VH2."FRAME_NUMBER" AS FRAME_NUMBER_H_HISTORY2,
                    VH2."HORSE_NUMBER" AS HORSE_NUMBER_H_HISTORY2,
                    VH2."BODY_WEIGHT" AS BODY_WEIGHT_H_HISTORY2,
                    VH2."JOCKEY" AS JOCKEY_H_HISTORY2,
                    VH2."ODDS" AS ODDS_H_HISTORY2,
                    VH2."POPULARITY" AS POPULARITY_H_HISTORY2,
                    VH2."RANK" AS RANK_H_HISTORY2,
                    VH2."TIME" AS TIME_H_HISTORY2,
                    VH2."TIME_DIFF" AS TIME_DIFF_H_HISTORY2,
                    VH2."TIME_UP" AS TIME_UP_H_HISTORY2,
                    VH2."PACE_1" AS PACE_1_H_HISTORY2,
                    VH2."PACE_2" AS PACE_2_H_HISTORY2,
                    VH2."POSITION_1" AS POSITION_1_H_HISTORY2,
                    VH2."POSITION_2" AS POSITION_2_H_HISTORY2,
                    VH2."POSITION_3" AS POSITION_3_H_HISTORY2,
                    VH2."POSITION_4" AS POSITION_4_H_HISTORY2,
                    VH2."WINNER" AS WINNER_H_HISTORY2,
                    VH2."PRIZE" AS PRIZE_H_HISTORY2,
                    COALESCE(VH2."NEW_FLG", false) AS NEW_FLG_H_HISTORY2,
                    COALESCE(VH2."G1_FLG", false) AS G1_FLG_H_HISTORY2,
                    COALESCE(VH2."G2_FLG", false) AS G2_FLG_H_HISTORY2,
                    COALESCE(VH2."G3_FLG", false) AS G3_FLG_H_HISTORY2,
                    COALESCE(VH2."L_FLG", false) AS L_FLG_H_HISTORY2,
                    COALESCE(VH2."NOT_WIN_FLG", false) AS NOT_WIN_FLG_H_HISTORY2,
                    COALESCE(VH2."OP_FLG", false) AS OP_FLG_H_HISTORY2,
                    COALESCE(VH2."WIN_1_FLG", false) AS WIN_1_FLG_H_HISTORY2,
                    COALESCE(VH2."WIN_2_FLG", false) AS WIN_2_FLG_H_HISTORY2,
                    COALESCE(VH2."WIN_3_FLG", false) AS WIN_3_FLG_H_HISTORY2,
                    VH3."RACE_DATE" AS RACE_DATE_H_HISTORY3,
                    VH3."RACE_NAME" AS RACE_NAME_H_HISTORY3,
                    VH3."PLACE_ID" AS PLACE_ID_H_HISTORY3,
                    VH3."PLACE_NAME" AS PLACE_NAME_H_HISTORY3,
                    VH3."TRACK_CONDITION" AS TRACK_CONDITION_H_HISTORY3,
                    VH3."WEATHER" AS WEATHER_H_HISTORY3,
                    VH3."COUNT" AS COUNT_H_HISTORY3,
                    VH3."FIELD" AS FIELD_H_HISTORY3,
                    VH3."DISTANCE" AS DISTANCE_H_HISTORY3,
                    VH3."FRAME_NUMBER" AS FRAME_NUMBER_H_HISTORY3,
                    VH3."HORSE_NUMBER" AS HORSE_NUMBER_H_HISTORY3,
                    VH3."BODY_WEIGHT" AS BODY_WEIGHT_H_HISTORY3,
                    VH3."JOCKEY" AS JOCKEY_H_HISTORY3,
                    VH3."ODDS" AS ODDS_H_HISTORY3,
                    VH3."POPULARITY" AS POPULARITY_H_HISTORY3,
                    VH3."RANK" AS RANK_H_HISTORY3,
                    VH3."TIME" AS TIME_H_HISTORY3,
                    VH3."TIME_DIFF" AS TIME_DIFF_H_HISTORY3,
                    VH3."TIME_UP" AS TIME_UP_H_HISTORY3,
                    VH3."PACE_1" AS PACE_1_H_HISTORY3,
                    VH3."PACE_2" AS PACE_2_H_HISTORY3,
                    VH3."POSITION_1" AS POSITION_1_H_HISTORY3,
                    VH3."POSITION_2" AS POSITION_2_H_HISTORY3,
                    VH3."POSITION_3" AS POSITION_3_H_HISTORY3,
                    VH3."POSITION_4" AS POSITION_4_H_HISTORY3,
                    VH3."WINNER" AS WINNER_H_HISTORY3,
                    VH3."PRIZE" AS PRIZE_H_HISTORY3,
                    COALESCE(VH3."NEW_FLG", false) AS NEW_FLG_H_HISTORY3,
                    COALESCE(VH3."G1_FLG", false) AS G1_FLG_H_HISTORY3,
                    COALESCE(VH3."G2_FLG", false) AS G2_FLG_H_HISTORY3,
                    COALESCE(VH3."G3_FLG", false) AS G3_FLG_H_HISTORY3,
                    COALESCE(VH3."L_FLG", false) AS L_FLG_H_HISTORY3,
                    COALESCE(VH3."NOT_WIN_FLG", false) AS NOT_WIN_FLG_H_HISTORY3,
                    COALESCE(VH3."OP_FLG", false) AS OP_FLG_H_HISTORY3,
                    COALESCE(VH3."WIN_1_FLG", false) AS WIN_1_FLG_H_HISTORY3,
                    COALESCE(VH3."WIN_2_FLG", false) AS WIN_2_FLG_H_HISTORY3,
                    COALESCE(VH3."WIN_3_FLG", false) AS WIN_3_FLG_H_HISTORY3,
                    VJ1."RACE_DATE" AS RACE_DATE_J_HISTORY1,
                    VJ1."RACE_NO" AS RACE_NO_J_HISTORY1,
                    VJ1."RACE_NAME" AS RACE_NAME_J_HISTORY1,
                    VJ1."TRACK_CONDITION" AS TRACK_CONDITION_J_HISTORY1,
                    VJ1."WEATHER" AS WEATHER_J_HISTORY1,
                    VJ1."PLACE_ID" AS PLACE_ID_J_HISTORY1,
                    VJ1."PLACE_NAME" AS PLACE_NAME_J_HISTORY1,
                    VJ1."COUNT" AS COUNT_J_HISTORY1,
                    VJ1."FIELD" AS FIELD_J_HISTORY1,
                    VJ1."DISTANCE" AS DISTANCE_J_HISTORY1,
                    VJ1."BODY_WEIGHT" AS BODY_WEIGHT_J_HISTORY1,
                    VJ1."WEIGHT" AS WEIGHT_J_HISTORY1,
                    VJ1."FRAME_NUMBER" AS FRAME_NUMBER_J_HISTORY1,
                    VJ1."HORSE_NUMBER" AS HORSE_NUMBER_J_HISTORY1,
                    VJ1."HORSE" AS HORSE_J_HISTORY1,
                    VJ1."RANK" AS RANK_J_HISTORY1,
                    VJ1."TIME" AS TIME_J_HISTORY1,
                    VJ1."TIME_DIFF" AS TIME_DIFF_J_HISTORY1,
                    VJ1."TIME_UP" AS TIME_UP_J_HISTORY1,
                    VJ1."PACE_1" AS PACE_1_J_HISTORY1,
                    VJ1."PACE_2" AS PACE_2_J_HISTORY1,
                    VJ1."POSITION_1" AS POSITION_1_J_HISTORY1,
                    VJ1."POSITION_2" AS POSITION_2_J_HISTORY1,
                    VJ1."POSITION_3" AS POSITION_3_J_HISTORY1,
                    VJ1."POSITION_4" AS POSITION_4_J_HISTORY1,
                    VJ1."ODDS" AS ODDS_J_HISTORY1,
                    VJ1."POPULARITY" AS POPULARITY_J_HISTORY1,
                    VJ1."WINNER" AS WINNER_J_HISTORY1,
                    VJ1."PRIZE" AS PRIZE_J_HISTORY1,
                    COALESCE(VJ1."WEIGHT_4KG_CUT_FLG", false) AS WEIGHT_4KG_CUT_FLG_J_HISTORY1,
                    COALESCE(VJ1."WEIGHT_3KG_CUT_FLG", false) AS WEIGHT_3KG_CUT_FLG_J_HISTORY1,
                    COALESCE(VJ1."WEIGHT_2KG_CUT_FLG", false) AS WEIGHT_2KG_CUT_FLG_J_HISTORY1,
                    COALESCE(VJ1."WEIGHT_1KG_CUT_FLG", false) AS WEIGHT_1KG_CUT_FLG_J_HISTORY1,
                    COALESCE(VJ1."WOMEN_WEIGHT_2KG_CUT_FLG", false) AS WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY1,
                    COALESCE(VJ1."NEW_FLG", false) AS NEW_FLG_J_HISTORY1,
                    COALESCE(VJ1."G1_FLG", false) AS G1_FLG_J_HISTORY1,
                    COALESCE(VJ1."G2_FLG", false) AS G2_FLG_J_HISTORY1,
                    COALESCE(VJ1."G3_FLG", false) AS G3_FLG_J_HISTORY1,
                    COALESCE(VJ1."L_FLG", false) AS L_FLG_J_HISTORY1,
                    COALESCE(VJ1."NOT_WIN_FLG", false) AS NOT_WIN_FLG_J_HISTORY1,
                    COALESCE(VJ1."OP_FLG", false) AS OP_FLG_J_HISTORY1,
                    COALESCE(VJ1."WIN_1_FLG", false) AS WIN_1_FLG_J_HISTORY1,
                    COALESCE(VJ1."WIN_2_FLG", false) AS WIN_2_FLG_J_HISTORY1,
                    COALESCE(VJ1."WIN_3_FLG", false) AS WIN_3_FLG_J_HISTORY1,
                    VJ2."RACE_DATE" AS RACE_DATE_J_HISTORY2,
                    VJ2."RACE_NO" AS RACE_NO_J_HISTORY2,
                    VJ2."RACE_NAME" AS RACE_NAME_J_HISTORY2,
                    VJ2."TRACK_CONDITION" AS TRACK_CONDITION_J_HISTORY2,
                    VJ2."WEATHER" AS WEATHER_J_HISTORY2,
                    VJ2."PLACE_ID" AS PLACE_ID_J_HISTORY2,
                    VJ2."PLACE_NAME" AS PLACE_NAME_J_HISTORY2,
                    VJ2."COUNT" AS COUNT_J_HISTORY2,
                    VJ2."FIELD" AS FIELD_J_HISTORY2,
                    VJ2."DISTANCE" AS DISTANCE_J_HISTORY2,
                    VJ2."BODY_WEIGHT" AS BODY_WEIGHT_J_HISTORY2,
                    VJ2."WEIGHT" AS WEIGHT_J_HISTORY2,
                    VJ2."FRAME_NUMBER" AS FRAME_NUMBER_J_HISTORY2,
                    VJ2."HORSE_NUMBER" AS HORSE_NUMBER_J_HISTORY2,
                    VJ2."HORSE" AS HORSE_J_HISTORY2,
                    VJ2."RANK" AS RANK_J_HISTORY2,
                    VJ2."TIME" AS TIME_J_HISTORY2,
                    VJ2."TIME_DIFF" AS TIME_DIFF_J_HISTORY2,
                    VJ2."TIME_UP" AS TIME_UP_J_HISTORY2,
                    VJ2."PACE_1" AS PACE_1_J_HISTORY2,
                    VJ2."PACE_2" AS PACE_2_J_HISTORY2,
                    VJ2."POSITION_1" AS POSITION_1_J_HISTORY2,
                    VJ2."POSITION_2" AS POSITION_2_J_HISTORY2,
                    VJ2."POSITION_3" AS POSITION_3_J_HISTORY2,
                    VJ2."POSITION_4" AS POSITION_4_J_HISTORY2,
                    VJ2."ODDS" AS ODDS_J_HISTORY2,
                    VJ2."POPULARITY" AS POPULARITY_J_HISTORY2,
                    VJ2."WINNER" AS WINNER_J_HISTORY2,
                    VJ2."PRIZE" AS PRIZE_J_HISTORY2,
                    COALESCE(VJ2."WEIGHT_4KG_CUT_FLG", false) AS WEIGHT_4KG_CUT_FLG_J_HISTORY2,
                    COALESCE(VJ2."WEIGHT_3KG_CUT_FLG", false) AS WEIGHT_3KG_CUT_FLG_J_HISTORY2,
                    COALESCE(VJ2."WEIGHT_2KG_CUT_FLG", false) AS WEIGHT_2KG_CUT_FLG_J_HISTORY2,
                    COALESCE(VJ2."WEIGHT_1KG_CUT_FLG", false) AS WEIGHT_1KG_CUT_FLG_J_HISTORY2,
                    COALESCE(VJ2."WOMEN_WEIGHT_2KG_CUT_FLG", false) AS WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY2,
                    COALESCE(VJ2."NEW_FLG", false) AS NEW_FLG_J_HISTORY2,
                    COALESCE(VJ2."G1_FLG", false) AS G1_FLG_J_HISTORY2,
                    COALESCE(VJ2."G2_FLG", false) AS G2_FLG_J_HISTORY2,
                    COALESCE(VJ2."G3_FLG", false) AS G3_FLG_J_HISTORY2,
                    COALESCE(VJ2."L_FLG", false) AS L_FLG_J_HISTORY2,
                    COALESCE(VJ2."NOT_WIN_FLG" , false)AS NOT_WIN_FLG_J_HISTORY2,
                    COALESCE(VJ2."OP_FLG", false) AS OP_FLG_J_HISTORY2,
                    COALESCE(VJ2."WIN_1_FLG", false) AS WIN_1_FLG_J_HISTORY2,
                    COALESCE(VJ2."WIN_2_FLG", false) AS WIN_2_FLG_J_HISTORY2,
                    COALESCE(VJ2."WIN_3_FLG", false) AS WIN_3_FLG_J_HISTORY2,
                    VJ3."RACE_DATE" AS RACE_DATE_J_HISTORY3,
                    VJ3."RACE_NO" AS RACE_NO_J_HISTORY3,
                    VJ3."RACE_NAME" AS RACE_NAME_J_HISTORY3,
                    VJ3."TRACK_CONDITION" AS TRACK_CONDITION_J_HISTORY3,
                    VJ3."WEATHER" AS WEATHER_J_HISTORY3,
                    VJ3."PLACE_ID" AS PLACE_ID_J_HISTORY3,
                    VJ3."PLACE_NAME" AS PLACE_NAME_J_HISTORY3,
                    VJ3."COUNT" AS COUNT_J_HISTORY3,
                    VJ3."FIELD" AS FIELD_J_HISTORY3,
                    VJ3."DISTANCE" AS DISTANCE_J_HISTORY3,
                    VJ3."BODY_WEIGHT" AS BODY_WEIGHT_J_HISTORY3,
                    VJ3."WEIGHT" AS WEIGHT_J_HISTORY3,
                    VJ3."FRAME_NUMBER" AS FRAME_NUMBER_J_HISTORY3,
                    VJ3."HORSE_NUMBER" AS HORSE_NUMBER_J_HISTORY3,
                    VJ3."HORSE" AS HORSE_J_HISTORY3,
                    VJ3."RANK" AS RANK_J_HISTORY3,
                    VJ3."TIME" AS TIME_J_HISTORY3,
                    VJ3."TIME_DIFF" AS TIME_DIFF_J_HISTORY3,
                    VJ3."TIME_UP" AS TIME_UP_J_HISTORY3,
                    VJ3."PACE_1" AS PACE_1_J_HISTORY3,
                    VJ3."PACE_2" AS PACE_2_J_HISTORY3,
                    VJ3."POSITION_1" AS POSITION_1_J_HISTORY3,
                    VJ3."POSITION_2" AS POSITION_2_J_HISTORY3,
                    VJ3."POSITION_3" AS POSITION_3_J_HISTORY3,
                    VJ3."POSITION_4" AS POSITION_4_J_HISTORY3,
                    VJ3."ODDS" AS ODDS_J_HISTORY3,
                    VJ3."POPULARITY" AS POPULARITY_J_HISTORY3,
                    VJ3."WINNER" AS WINNER_J_HISTORY3,
                    VJ3."PRIZE" AS PRIZE_J_HISTORY3,
                    COALESCE(VJ3."WEIGHT_4KG_CUT_FLG", false) AS WEIGHT_4KG_CUT_FLG_J_HISTORY3,
                    COALESCE(VJ3."WEIGHT_3KG_CUT_FLG", false) AS WEIGHT_3KG_CUT_FLG_J_HISTORY3,
                    COALESCE(VJ3."WEIGHT_2KG_CUT_FLG", false) AS WEIGHT_2KG_CUT_FLG_J_HISTORY3,
                    COALESCE(VJ3."WEIGHT_1KG_CUT_FLG", false) AS WEIGHT_1KG_CUT_FLG_J_HISTORY3,
                    COALESCE(VJ3."WOMEN_WEIGHT_2KG_CUT_FLG", false) AS WOMEN_WEIGHT_2KG_CUT_FLG_J_HISTORY3,
                    COALESCE(VJ3."NEW_FLG", false) AS NEW_FLG_J_HISTORY3,
                    COALESCE(VJ3."G1_FLG", false) AS G1_FLG_J_HISTORY3,
                    COALESCE(VJ3."G2_FLG", false) AS G2_FLG_J_HISTORY3,
                    COALESCE(VJ3."G3_FLG", false) AS G3_FLG_J_HISTORY3,
                    COALESCE(VJ3."L_FLG", false) AS L_FLG_J_HISTORY3,
                    COALESCE(VJ3."NOT_WIN_FLG", false) AS NOT_WIN_FLG_J_HISTORY3,
                    COALESCE(VJ3."OP_FLG", false) AS OP_FLG_J_HISTORY3,
                    COALESCE(VJ3."WIN_1_FLG", false) AS WIN_1_FLG_J_HISTORY3,
                    COALESCE(VJ3."WIN_2_FLG", false) AS WIN_2_FLG_J_HISTORY3,
                    COALESCE(VJ3."WIN_3_FLG", false) AS WIN_3_FLG_J_HISTORY3,
                    VR."RANK" AS RANK,
                    VR."RACE_TIME" AS RACE_TIME,
                    VR."CORNER_ORDER" AS CORNER_ORDER,
                    VR."POSITIONS" AS POSITIONS,
                    VR."POSITIONS_TIE" AS POSITIONS_TIE,
                    VR."PAY1" AS PAY1,
                    VR."PAY1_TIE" AS PAY1_TIE,
                    VR."PAY123_1" AS PAY123_1,
                    VR."PAY123_2" AS PAY123_2,
                    VR."PAY123_3" AS PAY123_3,
                    VR."PAY123_TIE" AS PAY123_TIE,
                    VR."PAY123_12_1" AS PAY123_12_1,
                    VR."PAY123_12_2" AS PAY123_12_2,
                    VR."PAY123_12_3" AS PAY123_12_3,
                    VR."PAY123_12_4_TIE" AS PAY123_12_4_TIE,
                    VR."PAY123_12_5_TIE" AS PAY123_12_5_TIE,
                    VR."PAY12_21" AS PAY12_21,
                    VR."PAY12_21_TIE" AS PAY12_21_TIE,
                    VR."PAY12_12" AS PAY12_12,
                    VR."PAY12_12_TIE" AS PAY12_12_TIE,
                    VR."PAY123_321" AS PAY123_321,
                    VR."PAY123_321_TIE" AS PAY123_321_TIE,
                    VR."PAY123_123" AS PAY123_123,
                    VR."PAY123_123_TIE" AS PAY123_123_TIE
                    
                FROM t_final_base_info VB_MAIN
                LEFT JOIN t_final_horse_info VH1
                    ON VB_MAIN."HORSE_ID" = VH1."HORSE_ID"
                    AND VB_MAIN."TODAY_RACE_DATE" = VH1."TODAY_RACE_DATE"
                    AND VH1."GR_ID" = 1
                LEFT JOIN t_final_horse_info VH2
                    ON VB_MAIN."HORSE_ID" = VH2."HORSE_ID"
                    AND VB_MAIN."TODAY_RACE_DATE" = VH2."TODAY_RACE_DATE"
                    AND VH2."GR_ID" = 2
                LEFT JOIN t_final_horse_info VH3
                    ON VB_MAIN."HORSE_ID" = VH3."HORSE_ID"
                    AND VB_MAIN."TODAY_RACE_DATE" = VH3."TODAY_RACE_DATE"
                    AND VH3."GR_ID" = 3
                LEFT JOIN t_final_jockey_info VJ1
                    ON VB_MAIN."JOCKEY_ID" = VJ1."JOCKEY_ID"
                    AND VB_MAIN."TODAY_RACE_DATE" = VJ1."TODAY_RACE_DATE"
                    AND VB_MAIN."TODAY_RACE_NO" = VJ1."TODAY_RACE_NO"
                    AND VJ1."GR_ID" = 1
                LEFT JOIN t_final_jockey_info VJ2
                    ON VB_MAIN."JOCKEY_ID" = VJ2."JOCKEY_ID"
                    AND VB_MAIN."TODAY_RACE_DATE" = VJ2."TODAY_RACE_DATE"
                    AND VB_MAIN."TODAY_RACE_NO" = VJ2."TODAY_RACE_NO"
                    AND VJ2."GR_ID" = 2
                LEFT JOIN t_final_jockey_info VJ3
                    ON VB_MAIN."JOCKEY_ID" = VJ3."JOCKEY_ID"
                    AND VB_MAIN."TODAY_RACE_DATE" = VJ3."TODAY_RACE_DATE"
                    AND VB_MAIN."TODAY_RACE_NO" = VJ3."TODAY_RACE_NO"
                    AND VJ3."GR_ID" = 3
                LEFT JOIN t_final_result_info VR
                    ON VB_MAIN."RACE_ID" = VR."RACE_ID"
                    AND VB_MAIN."HORSE_NUMBER" = VR."HORSE_NUMBER"
                ORDER BY VB_MAIN."TODAY_RACE_DATE" DESC, VB_MAIN."TODAY_RACE_NO", VB_MAIN."HORSE_NUMBER";
        """)
