#!/usr/bin/env python3
"""
@file    build_dataset_pandas.py
@brief   t_base_info + t_result_info から pandas で直接、学習用CSVを構築する
@version 1.0.0  2026-06-28  新規作成 (Dicky1114)

経緯:
  旧 run_full_pipeline の step4 は未コミットのDBビュー(v_base_info 等)と
  HorseData/JockeyData 追加スクレイプに依存し復元コストが高い。
  本スクリプトは scrape 済みの base/result のみから、リーク防止しつつ
  ml_training.py の入力契約に合うCSVを生成する。

特徴量設計(すべて「事前(出走前)」に既知の情報のみ):
  - レースカード: 枠/馬番/性/年齢/斤量/馬体重/増減/オッズ/人気/距離/馬場/天候/頭数/競馬場/格
  - 馬の過去成績: groupby(horse_id)+shift で「過去レースのみ」から算出
      prev_rank / avg_rank3 / n_runs_prior / days_since_last /
      prev_popularity / prev_last3f / win_rate_prior / place_rate_prior
  - 騎手: 累積(過去のみ)勝率/複勝率
  - 結果列(rank/race_time/last_3f/corner/pay*)はバックテスト用に保持
    (ml_training.RESULT_COLS が特徴量から自動除外する=リークしない)

使用方法:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/build_dataset_pandas.py
"""

import os
import sys
import re
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')

import django
django.setup()

import numpy as np
import pandas as pd
from django.conf import settings
from django.db import connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def _to_num(s):
    return pd.to_numeric(s, errors='coerce')


def load_frames() -> pd.DataFrame:
    """base と result を結合して1行=1出走馬のDataFrameを返す。"""
    base = pd.read_sql(
        """
        SELECT race_id, horse_number, frame_number, horse_name, race_date,
               sex, age, weight, body_weight, body_weight_diff, odds, popularity,
               distance_m, field_type, track_condition, weather, count, race_place,
               new_flg, not_win_flg, win_1_flg, win_2_flg, win_3_flg,
               g1_flg, g2_flg, g3_flg, l_flg, op_flg,
               horse_url, jockey_url, stable_name
        FROM t_base_info
        """,
        connection,
    )
    result = pd.read_sql(
        """
        SELECT race_id, horse_number, rank, race_time, last_3f, corner_order,
               pay1, pay123_1, pay123_2, pay123_3,
               pay12_12, pay12_21, pay123_123, pay123_321
        FROM t_result_info
        """,
        connection,
    )
    df = base.merge(result, on=['race_id', 'horse_number'], how='inner')
    logger.info(f"結合: base={len(base)} result={len(result)} → merged={len(df)}")
    return df


def add_ids_and_keys(df: pd.DataFrame) -> pd.DataFrame:
    """horse_id/jockey_id 抽出 + 並び替えキー整備。"""
    df['horse_id'] = df['horse_url'].astype(str).str.extract(r'/horse/(\w+)')
    df['jockey_id'] = df['jockey_url'].astype(str).str.extract(r'/jockey/(?:result/recent/)?(\w+)')
    df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce', utc=True).dt.tz_localize(None)
    df['today_race_date'] = df['race_date'].dt.strftime('%Y-%m-%d')
    # 数値化
    for c in ['horse_number', 'frame_number', 'age', 'weight', 'body_weight',
              'body_weight_diff', 'odds', 'popularity', 'distance_m', 'count']:
        df[c] = _to_num(df[c])
    df['rank_num'] = _to_num(df['rank'])
    # レース内での発走順序の安定化: race_id 昇順 → 馬番
    df = df.sort_values(['race_date', 'race_id', 'horse_number']).reset_index(drop=True)
    return df


def _parse_time(s):
    """'M:SS.s' → 秒。'1:12.1'→72.1。不正は NaN。"""
    try:
        s = str(s).strip()
        if ':' in s:
            m, rest = s.split(':', 1)
            return float(m) * 60 + float(rest)
        return float(s)
    except (ValueError, AttributeError):
        return np.nan


def add_speed_figures(df: pd.DataFrame) -> pd.DataFrame:
    """走破タイムを距離×コース×馬場で正規化し、日次馬場差で補正したスピード指数。

    speed_fig = (par - 実タイム) - その日の馬場差 + 斤量補正
      par   : (距離, 馬場種別) ごとの中央値タイム
      馬場差: (レース日, 競馬場, 馬場種別) の (par-実タイム) 平均(=その日全体の速さ)
    値が大きいほど速い。当該レースの speed_fig は特徴量にせず、
    各馬の「過去走の speed_fig」を shift で前走能力指標として使う。
    """
    df = df.copy()
    # 末脚指標: 各レース内の上がり3F順位(小さい=速い末脚)。過去走をshiftして使う(add_horse_history)
    df['last3f_num'] = _to_num(df['last_3f'])
    df['last3f_rank'] = df.groupby('race_id')['last3f_num'].rank(method='min', ascending=True)
    df['time_sec'] = df['race_time'].apply(_parse_time)
    valid = df['time_sec'].notna() & df['distance_m'].notna()

    # par: (距離, 馬場種別) の中央値
    par = df[valid].groupby(['distance_m', 'field_type'])['time_sec'].median().rename('par')
    df = df.merge(par, on=['distance_m', 'field_type'], how='left')
    df['raw_fig'] = df['par'] - df['time_sec']  # 速い=正

    # 日次馬場差: (日, 競馬場, 馬場種別) の raw_fig 平均
    variant = (df[valid].groupby([df['race_date'].dt.date, 'race_place', 'field_type'])['raw_fig']
               .transform('mean'))
    df['track_variant'] = variant
    # 斤量補正(1kg≒0.2秒、軽いほど速く見えるので重い分を加点)
    wadj = (df['weight'] - 55.0) * 0.2
    df['speed_fig'] = (df['raw_fig'] - df['track_variant'].fillna(0) + wadj.fillna(0))
    return df


def add_pedigree(df: pd.DataFrame) -> pd.DataFrame:
    """血統(父)を結合。父をカテゴリ特徴に、父の累積勝率(過去のみ=shift)を数値特徴にする。"""
    path = os.path.join(settings.MEDIA_ROOT, 'csv_export', 'pedigree.csv')
    if not os.path.exists(path):
        df['sire'] = ''
        df['sire_win_rate'] = np.nan
        return df
    pcols = ['horse_id', 'sire']
    _ped_all = pd.read_csv(path, dtype=str)
    if 'broodmare_sire' in _ped_all.columns:
        pcols.append('broodmare_sire')
    ped = _ped_all[pcols].drop_duplicates('horse_id')
    df = df.merge(ped, on='horse_id', how='left')
    df['sire'] = df['sire'].fillna('')
    if 'broodmare_sire' in df.columns:
        df['broodmare_sire'] = df['broodmare_sire'].fillna('')
    else:
        df['broodmare_sire'] = ''
    # 父の累積勝率(リーク防止: 当該レースを含めない)
    d = df.sort_values(['race_date', 'race_id']).reset_index(drop=True)
    is_win = (pd.to_numeric(d['rank'], errors='coerce') == 1).astype(float)
    g = is_win.groupby(d['sire'])
    cum_win = g.cumsum() - is_win
    cum_n = d.groupby('sire').cumcount()
    d['sire_win_rate'] = (cum_win / cum_n.replace(0, np.nan))
    return d


def add_running_style(df: pd.DataFrame) -> pd.DataFrame:
    """corner_order(各コーナー通過順)から脚質=序盤位置を算出する。
    first_corner_pos = 最初のコーナー位置, early_pos_ratio = 位置/頭数(0=先頭,1=最後方)。
    当該レースの位置は結果なので、過去走をshiftして「その馬の脚質傾向」を事前特徴にする。"""
    def first_pos(v):
        m = re.match(r'\s*(\d+)', str(v))
        return int(m.group(1)) if m else np.nan
    df = df.copy()
    df['first_corner_pos'] = df['corner_order'].apply(first_pos)
    cnt = _to_num(df['count']).replace(0, np.nan)
    df['early_pos_ratio'] = df['first_corner_pos'] / cnt
    return df


def add_oikiri(df: pd.DataFrame) -> pd.DataFrame:
    """調教評価CSV(scrape_oikiri_urllib.py出力)を race_id+horse_number で結合する。
    調教は出走前に確定するため当該レースの評価をそのまま特徴量に使える(リーク無し)。"""
    path = os.path.join(settings.MEDIA_ROOT, 'csv_export', 'oikiri_grades.csv')
    if not os.path.exists(path):
        df['oikiri_grade'] = np.nan
        return df
    o = pd.read_csv(path)
    o['race_id'] = o['race_id'].astype(str)
    o['horse_number'] = _to_num(o['horse_number'])
    o['oikiri_grade'] = _to_num(o['oikiri_grade'])
    cols = ['race_id', 'horse_number', 'oikiri_grade']
    if 'oikiri_sentiment' in o.columns:
        o['oikiri_sentiment'] = _to_num(o['oikiri_sentiment'])
        cols.append('oikiri_sentiment')
    df['race_id'] = df['race_id'].astype(str)
    df = df.merge(o[cols], on=['race_id', 'horse_number'], how='left')
    return df


def add_race_class(df: pd.DataFrame) -> pd.DataFrame:
    """レースクラス(新馬〜G1)をHTML由来CSVから結合。出走前に既知=リーク無し。
    class_level=能力序列(順序数), race_class=カテゴリ。
    さらに昇降級(前走クラスとの差)を過去走shiftで作る。"""
    path = os.path.join(settings.MEDIA_ROOT, 'csv_export', 'race_class.csv')
    if not os.path.exists(path):
        df['race_class'] = '不明'
        df['class_level'] = np.nan
        return df
    rc = pd.read_csv(path, dtype={'race_id': str})
    df['race_id'] = df['race_id'].astype(str)
    df = df.merge(rc[['race_id', 'race_class', 'class_level']], on='race_id', how='left')
    df['class_level'] = _to_num(df['class_level']).replace(-1, np.nan)
    df['race_class'] = df['race_class'].fillna('不明')
    return df


def _past_cond_stats(df, keycols, prefix, is_win, is_place):
    """key(馬+条件)ごとの『現行を含めない』過去成績を返す(リーク防止)。
    戻り: runs/winrate/placerate/avgspeed の4列を df に付与。"""
    key = df.groupby(keycols, sort=False)
    runs = key.cumcount()                                  # 過去出走数(現行除く)
    win_prior = is_win.groupby([df[k] for k in keycols]).cumsum() - is_win
    pl_prior = is_place.groupby([df[k] for k in keycols]).cumsum() - is_place
    df[f'{prefix}_runs'] = runs
    df[f'{prefix}_winrate'] = win_prior / runs.replace(0, np.nan)
    df[f'{prefix}_placerate'] = pl_prior / runs.replace(0, np.nan)
    if 'speed_fig' in df.columns:
        sp = df['speed_fig']; spf = sp.fillna(0); nn = sp.notna().astype(float)
        csum = spf.groupby([df[k] for k in keycols]).cumsum() - spf
        cnt = nn.groupby([df[k] for k in keycols]).cumsum() - nn
        df[f'{prefix}_avgspeed'] = csum / cnt.replace(0, np.nan)
    return df


def add_conditional_history(df: pd.DataFrame) -> pd.DataFrame:
    """条件別適性(競馬で最重要級): この馬の【同距離帯/同芝ダ/同コース】での過去成績。
    すべて『過去走のみ』(現行レースを累積から引く)でリーク防止。"""
    df = df.copy()
    df['dist_band'] = pd.cut(_to_num(df['distance_m']),
                             [0, 1300, 1600, 2000, 2400, 99999],
                             labels=['短', 'マ', '中', '中長', '長'])
    is_win = (df['rank_num'] == 1).astype(float)
    is_place = (df['rank_num'] <= 3).astype(float)
    # 同芝ダ
    df = df.sort_values(['horse_id', 'field_type', 'race_date', 'race_id']).reset_index(drop=True)
    is_win = (df['rank_num'] == 1).astype(float); is_place = (df['rank_num'] <= 3).astype(float)
    df = _past_cond_stats(df, ['horse_id', 'field_type'], 'ft', is_win, is_place)
    # 同距離帯
    df = df.sort_values(['horse_id', 'dist_band', 'race_date', 'race_id']).reset_index(drop=True)
    is_win = (df['rank_num'] == 1).astype(float); is_place = (df['rank_num'] <= 3).astype(float)
    df = _past_cond_stats(df, ['horse_id', 'dist_band'], 'dist', is_win, is_place)
    # 同コース(競馬場)
    df = df.sort_values(['horse_id', 'race_place', 'race_date', 'race_id']).reset_index(drop=True)
    is_win = (df['rank_num'] == 1).astype(float); is_place = (df['rank_num'] <= 3).astype(float)
    df = _past_cond_stats(df, ['horse_id', 'race_place'], 'course', is_win, is_place)
    return df


def add_class_and_misc(df: pd.DataFrame) -> pd.DataFrame:
    """昇降級・休養・枠順・負担率などの素直な特徴(全て出走前に既知 or 過去shift)。"""
    df = df.sort_values(['horse_id', 'race_date', 'race_id']).reset_index(drop=True)
    g = df.groupby('horse_id', sort=False)
    # 昇降級: 前走クラス − 今走クラス(+ = 今走が格下げ=楽, − = 格上挑戦)
    if 'class_level' in df.columns:
        df['prev_class_level'] = g['class_level'].shift(1)
        df['class_drop'] = df['prev_class_level'] - df['class_level']
    # 休養区分(rotation): days_since_last を意味のある帯に
    if 'days_since_last' in df.columns:
        df['layoff_long'] = (_to_num(df['days_since_last']) >= 90).astype(float)   # 休み明け
        df['layoff_short'] = (_to_num(df['days_since_last']) <= 14).astype(float)  # 連闘・詰め
    # 枠順バイアス(外枠不利の代理): 枠/頭数, 馬番/頭数
    cnt = _to_num(df['count']).replace(0, np.nan)
    df['frame_ratio'] = _to_num(df['frame_number']) / cnt
    df['post_ratio'] = _to_num(df['horse_number']) / cnt
    # 負担率(斤量/馬体重)・馬体重の絶対水準
    df['weight_ratio'] = _to_num(df['weight']) / _to_num(df['body_weight']).replace(0, np.nan)
    # 交互作用: 道悪×脚質(過去の位置取り), 距離×脚質
    if 'avg_early_pos3' in df.columns:
        going_bad = df['track_condition'].isin(['重', '不良']).astype(float)
        df['ix_going_pos'] = going_bad * _to_num(df['avg_early_pos3'])
        df['ix_dist_pos'] = _to_num(df['distance_m']) * _to_num(df['avg_early_pos3'])
    return df


def add_pace(df: pd.DataFrame) -> pd.DataFrame:
    """展開(ペース): レース内の先行馬頭数 + 自分の脚質×展開。
    各馬の『過去の脚質』(avg_early_pos3=shift済)から推定するためリーク無し。
    先行馬過多→差し有利の地合い、を市場が言語化しづらい残差として狙う。"""
    if 'avg_early_pos3' not in df.columns:
        return df
    ep = _to_num(df['avg_early_pos3'])           # 0=先頭,1=最後方(過去平均)
    df['_is_front'] = (ep < 0.35).astype(float)  # 先行・逃げ馬
    df['pace_pressure'] = df.groupby('race_id')['_is_front'].transform('sum')  # レース内先行頭数
    # 自分の脚質 × 展開(差し馬は先行多で有利・逃げ馬は先行多で不利)
    df['style_x_pace'] = ep * df['pace_pressure']
    df.drop(columns=['_is_front'], inplace=True)
    return df


def add_horse_history(df: pd.DataFrame) -> pd.DataFrame:
    """馬の過去成績特徴を shift で算出(未来情報を使わない)。"""
    df = df.sort_values(['horse_id', 'race_date', 'race_id']).reset_index(drop=True)
    g = df.groupby('horse_id', sort=False)

    # 前走情報(直前レースのみ)
    df['prev_rank'] = g['rank_num'].shift(1)
    df['prev_popularity'] = g['popularity'].shift(1)
    df['prev_last3f'] = _to_num(g['last_3f'].shift(1))
    df['prev_odds'] = g['odds'].shift(1)
    df['days_since_last'] = (df['race_date'] - g['race_date'].shift(1)).dt.days

    # スピード指数の過去走特徴(当該レースは使わず shift で過去のみ)
    if 'speed_fig' in df.columns:
        df['prev_speed'] = g['speed_fig'].shift(1)
        prev_speed = g['speed_fig'].shift(1)
        df['avg_speed3'] = prev_speed.groupby(df['horse_id']).rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
        df['best_speed'] = prev_speed.groupby(df['horse_id']).cummax().reset_index(level=0, drop=True)
        # 成長率/トレンド(移動率): 前走 - 前々走 / 前走 - 直近平均
        df['prev2_speed'] = g['speed_fig'].shift(2)
        df['speed_trend'] = df['prev_speed'] - df['prev2_speed']        # +なら上昇基調
        df['speed_momentum'] = df['prev_speed'] - df['avg_speed3']      # 直近が平均より上か

    # 着順トレンド(良化/悪化)
    df['prev2_rank'] = g['rank_num'].shift(2)
    df['rank_trend'] = df['prev2_rank'] - df['prev_rank']              # +なら着順良化

    # 脚質(序盤位置)の過去走傾向 = 事前に既知の走法
    if 'early_pos_ratio' in df.columns:
        df['prev_early_pos'] = g['early_pos_ratio'].shift(1)
        prev_ep = g['early_pos_ratio'].shift(1)
        df['avg_early_pos3'] = prev_ep.groupby(df['horse_id']).rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)

    # 末脚指標(過去走の上がり3F順位・小さい=鋭い末脚) = 事前に既知
    if 'last3f_rank' in df.columns:
        df['prev_last3f_rank'] = g['last3f_rank'].shift(1)
        prev_l3 = g['last3f_rank'].shift(1)
        df['avg_last3f_rank3'] = prev_l3.groupby(df['horse_id']).rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)

    # 過去N走の集計(現レースを含めないため shift 後に rolling)
    prev_rank_series = g['rank_num'].shift(1)
    df['avg_rank3'] = prev_rank_series.groupby(df['horse_id']).rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
    df['best_rank_prior'] = prev_rank_series.groupby(df['horse_id']).cummin().reset_index(level=0, drop=True)

    # 出走数・勝率・複勝率(過去のみ=cumcount / cumsum を shift)
    df['n_runs_prior'] = g.cumcount()
    is_win = (df['rank_num'] == 1).astype(float)
    is_place = (df['rank_num'] <= 3).astype(float)
    df['win_rate_prior'] = (g_cumshift(df, 'horse_id', is_win)) / df['n_runs_prior'].replace(0, np.nan)
    df['place_rate_prior'] = (g_cumshift(df, 'horse_id', is_place)) / df['n_runs_prior'].replace(0, np.nan)
    return df


def add_jockey_history(df: pd.DataFrame) -> pd.DataFrame:
    """騎手の過去(累積・shift)勝率/複勝率。"""
    df = df.sort_values(['jockey_id', 'race_date', 'race_id']).reset_index(drop=True)
    g = df.groupby('jockey_id', sort=False)
    df['j_runs_prior'] = g.cumcount()
    is_win = (df['rank_num'] == 1).astype(float)
    is_place = (df['rank_num'] <= 3).astype(float)
    df['j_win_rate_prior'] = g_cumshift(df, 'jockey_id', is_win) / df['j_runs_prior'].replace(0, np.nan)
    df['j_place_rate_prior'] = g_cumshift(df, 'jockey_id', is_place) / df['j_runs_prior'].replace(0, np.nan)
    return df


def add_trainer_history(df: pd.DataFrame) -> pd.DataFrame:
    """調教師(厩舎)の過去(累積・shift)勝率/複勝率。stable_name をキーに。"""
    df['stable_name'] = df.get('stable_name', '').fillna('')
    df = df.sort_values(['stable_name', 'race_date', 'race_id']).reset_index(drop=True)
    g = df.groupby('stable_name', sort=False)
    df['t_runs_prior'] = g.cumcount()
    is_win = (df['rank_num'] == 1).astype(float)
    is_place = (df['rank_num'] <= 3).astype(float)
    df['t_win_rate_prior'] = g_cumshift(df, 'stable_name', is_win) / df['t_runs_prior'].replace(0, np.nan)
    df['t_place_rate_prior'] = g_cumshift(df, 'stable_name', is_place) / df['t_runs_prior'].replace(0, np.nan)
    return df


def add_relative(df: pd.DataFrame) -> pd.DataFrame:
    """レース内相対特徴: 各馬の過去指標を、同レース出走馬の平均と比較(事前に既知)。"""
    for col, rel in [('prev_speed', 'rel_prev_speed'), ('avg_speed3', 'rel_avg_speed3'),
                     ('avg_rank3', 'rel_avg_rank3'), ('prev_last3f_rank', 'rel_last3f_rank')]:
        if col in df.columns:
            df[rel] = df[col] - df.groupby('race_id')[col].transform('mean')
    return df


def g_cumshift(df: pd.DataFrame, key: str, values: pd.Series) -> pd.Series:
    """key ごとの「現行を含めない累積和」= cumsum を1つ shift。"""
    tmp = values.groupby(df[key]).cumsum() - values  # 現行を引く = 過去累積
    return tmp


def build() -> str:
    df = load_frames()
    if df.empty:
        logger.error("データが空です。先に scrape を完了してください。")
        sys.exit(1)
    df = add_ids_and_keys(df)
    df = add_race_class(df)       # クラス(新馬〜G1・HTML由来=死フラグの正しい代替)
    df = add_pedigree(df)        # 血統(父+父勝率)を結合
    df = add_oikiri(df)          # 調教評価(出走前確定=リーク無し)を結合
    df = add_running_style(df)   # 脚質(corner_order由来・過去走をshiftして使う)
    df = add_speed_figures(df)   # スピード指数(過去走特徴の素)を先に算出
    df = add_horse_history(df)
    df = add_jockey_history(df)
    df = add_trainer_history(df)  # 調教師(厩舎)成績
    df = add_conditional_history(df)  # 条件別適性(同距離帯/芝ダ/コースの過去成績・最重要級)
    df = add_class_and_misc(df)       # 昇降級/休養/枠順/負担率/交互作用
    df = add_pace(df)                 # 展開(レース内先行頭数・脚質×ペース)
    df = add_relative(df)         # レース内相対特徴(成長率/相対指数)

    # 最終並び (ml_training は ORDER_COLS で再ソートする)
    df = df.sort_values(['race_date', 'race_id', 'horse_number']).reset_index(drop=True)

    # 市場示唆確率(オッズから) = バックテストのバリュー判定にも使う
    df['implied_prob'] = 0.8 / df['odds']  # 単勝控除~20%概算

    # 出力列: グループ/ラベル + 特徴量 + 払戻(結果列)
    # WHY: horse_number はキー前置に含めるので feature からは除外(二重出力=horse_number.1 防止)。
    #      race_time/last_3f/corner_order は「当該レースの結果」= リークなので出力しない。
    #      前走情報 prev_last3f 等(shift済)のみ特徴量として保持する。
    feature_cols = [
        'frame_number', 'sex', 'age', 'weight', 'body_weight',
        'body_weight_diff', 'odds', 'popularity', 'implied_prob', 'distance_m',
        'field_type', 'track_condition', 'weather', 'count', 'race_place',
        # クラス(死フラグ win_x/g_x/l の正しい代替)
        'race_class', 'class_level', 'prev_class_level', 'class_drop',
        'new_flg', 'not_win_flg', 'op_flg',
        'prev_rank', 'prev_popularity', 'prev_last3f', 'prev_odds', 'days_since_last',
        'avg_rank3', 'best_rank_prior', 'n_runs_prior', 'win_rate_prior', 'place_rate_prior',
        'j_runs_prior', 'j_win_rate_prior', 'j_place_rate_prior',
        'prev_speed', 'avg_speed3', 'best_speed',
        'oikiri_grade', 'oikiri_sentiment',
        'prev_early_pos', 'avg_early_pos3',
        'sire', 'sire_win_rate', 'broodmare_sire',
        'prev_last3f_rank', 'avg_last3f_rank3',
        # 成長率/トレンド・調教師・レース内相対
        'prev2_speed', 'speed_trend', 'speed_momentum', 'prev2_rank', 'rank_trend',
        't_runs_prior', 't_win_rate_prior', 't_place_rate_prior',
        'rel_prev_speed', 'rel_avg_speed3', 'rel_avg_rank3', 'rel_last3f_rank',
        # 条件別適性(同芝ダ/同距離帯/同コースの過去成績・最重要級)
        'ft_runs', 'ft_winrate', 'ft_placerate', 'ft_avgspeed',
        'dist_runs', 'dist_winrate', 'dist_placerate', 'dist_avgspeed',
        'course_runs', 'course_winrate', 'course_placerate', 'course_avgspeed',
        # 休養/枠順/負担率/交互作用/展開
        'layoff_long', 'layoff_short', 'frame_ratio', 'post_ratio', 'weight_ratio',
        'ix_going_pos', 'ix_dist_pos', 'pace_pressure', 'style_x_pace',
    ]
    # 結果列はバックテスト用のみ(rank=着順ラベル + 払戻 + タイム回帰用target_time)。
    # target_time は「タイム目的変数」実験用。特徴量には使わない(後出し情報)。
    if 'time_sec' in df.columns:
        df['target_time'] = df['time_sec']
    else:
        df['target_time'] = np.nan
    result_cols = ['rank', 'target_time',
                   'pay1', 'pay123_1', 'pay123_2', 'pay123_3',
                   'pay12_12', 'pay12_21', 'pay123_123', 'pay123_321']
    keep = ['today_race_date', 'race_id', 'horse_number'] + feature_cols + result_cols
    out = df[keep].copy()

    csv_dir = os.path.join(settings.MEDIA_ROOT, 'csv_export')
    os.makedirs(csv_dir, exist_ok=True)
    csv_path = os.path.join(csv_dir, f"train_data_pandas_{datetime.now():%Y%m%d_%H%M}.csv")
    out.to_csv(csv_path, index=False)

    n_races = out['race_id'].nunique()
    logger.info(f"CSV出力: {csv_path}")
    logger.info(f"  行数={len(out)} レース数={n_races} 特徴量={len(feature_cols)}")
    logger.info(f"  rank分布(上位): \n{out['rank'].value_counts().head(6).to_string()}")
    return csv_path


if __name__ == '__main__':
    build()
