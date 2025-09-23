"""
共通ユーティリティ関数
"""
import hashlib
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def generate_race_id(venue_code, race_date, race_number):
    """
    レースIDを生成
    形式: YYYYMMDDVVRR (年月日+競馬場コード+レース番号)
    """
    date_str = race_date.strftime('%Y%m%d') if hasattr(race_date, 'strftime') else race_date
    return f"{date_str}{venue_code:02d}{race_number:02d}"


def parse_race_id(race_id):
    """
    レースIDをパース
    """
    if len(race_id) != 12:
        raise ValueError("レースIDの形式が正しくありません")
    
    year = int(race_id[:4])
    month = int(race_id[4:6])
    day = int(race_id[6:8])
    venue_code = int(race_id[8:10])
    race_number = int(race_id[10:12])
    
    race_date = datetime(year, month, day).date()
    
    return {
        'race_date': race_date,
        'venue_code': venue_code,
        'race_number': race_number
    }


def format_time(seconds):
    """
    秒数をMM:SS.f形式に変換
    """
    if not seconds:
        return None
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    return f"{minutes}:{remaining_seconds:04.1f}"


def parse_time(time_str):
    """
    MM:SS.f形式の時間を秒数に変換
    """
    if not time_str:
        return None
    
    try:
        parts = time_str.split(':')
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    except (ValueError, IndexError):
        return None


def calculate_win_rate(wins, total_races):
    """
    勝率を計算
    """
    if total_races == 0:
        return 0.0
    return (wins / total_races) * 100


def calculate_place_rate(places, total_races):
    """
    複勝率を計算（1-3着）
    """
    if total_races == 0:
        return 0.0
    return (places / total_races) * 100


def normalize_horse_name(name):
    """
    馬名を正規化（全角・半角統一など）
    """
    if not name:
        return name
    
    # 全角英数字を半角に変換
    name = name.translate(str.maketrans(
        '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
        '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ))
    
    # 余分な空白を削除
    name = re.sub(r'\s+', '', name)
    
    return name.strip()


def normalize_jockey_name(name):
    """
    騎手名を正規化
    """
    if not name:
        return name
    
    # 騎手名の後ろの☆などの記号を削除
    name = re.sub(r'[☆★◎○▲△]', '', name)
    
    # 余分な空白を削除
    name = re.sub(r'\s+', ' ', name)
    
    return name.strip()


def get_track_condition_weight(condition):
    """
    馬場状態による重み係数を取得
    """
    weights = {
        'firm': 1.0,    # 良
        'good': 0.95,   # 稍重
        'yielding': 0.9, # 重
        'soft': 0.85    # 不良
    }
    return weights.get(condition, 1.0)


def get_weather_weight(weather):
    """
    天候による重み係数を取得
    """
    weights = {
        'fine': 1.0,    # 晴
        'cloudy': 0.98, # 曇
        'rainy': 0.9,   # 雨
        'snowy': 0.85   # 雪
    }
    return weights.get(weather, 1.0)


def get_race_class_weight(race_class):
    """
    レースクラスによる重み係数を取得
    """
    weights = {
        'g1': 1.5,
        'g2': 1.3,
        'g3': 1.2,
        'listed': 1.1,
        'special': 1.05,
        '3win': 1.0,
        '2win': 0.95,
        '1win': 0.9,
        'maiden': 0.8,
        'novice': 0.7
    }
    return weights.get(race_class, 1.0)


def calculate_age_from_birth_date(birth_date):
    """
    生年月日から現在の年齢を計算
    """
    if not birth_date:
        return None
    
    today = timezone.now().date()
    age = today.year - birth_date.year
    
    # 誕生日前なら年齢を1減らす
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    
    return age


def get_season_from_date(date):
    """
    日付から季節を取得
    """
    month = date.month
    if month in [12, 1, 2]:
        return 'winter'
    elif month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    else:
        return 'autumn'


def is_weekend(date):
    """
    週末かどうかを判定
    """
    return date.weekday() >= 5  # 土曜日(5)、日曜日(6)


def get_next_race_dates(days=7):
    """
    今後のレース開催日を取得
    """
    today = timezone.now().date()
    dates = []
    
    for i in range(days):
        date = today + timedelta(days=i)
        if is_weekend(date):
            dates.append(date)
    
    return dates


def create_cache_key(*args, **kwargs):
    """
    キャッシュキーを生成
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}_{v}" for k, v in sorted(kwargs.items())])
    
    key = "_".join(key_parts)
    
    # キーが長すぎる場合はハッシュ化
    if len(key) > 200:
        key = hashlib.md5(key.encode()).hexdigest()
    
    return key


def safe_divide(numerator, denominator, default=0):
    """
    安全な除算（ゼロ除算エラー回避）
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default


def log_performance(func_name, start_time, end_time, extra_info=None):
    """
    処理時間をログ出力
    """
    duration = end_time - start_time
    message = f"Performance: {func_name} took {duration:.3f} seconds"
    
    if extra_info:
        message += f" | {extra_info}"
    
    logger.info(message)


def sanitize_filename(filename):
    """
    ファイル名から危険な文字を除去
    """
    # 危険な文字を削除
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 連続するスペースを単一のスペースに
    filename = re.sub(r'\s+', ' ', filename)
    return filename.strip()


def format_currency(amount):
    """
    金額をフォーマット（カンマ区切り）
    """
    if amount is None:
        return "0"
    return f"{amount:,}"


def parse_odds(odds_str):
    """
    オッズ文字列を数値に変換
    """
    if not odds_str:
        return None
    
    try:
        # 小数点形式 (例: "3.5")
        return float(odds_str)
    except ValueError:
        # 分数形式 (例: "7/2") の場合
        if '/' in odds_str:
            try:
                parts = odds_str.split('/')
                return float(parts[0]) / float(parts[1]) + 1.0
            except (ValueError, IndexError, ZeroDivisionError):
                return None
        return None
