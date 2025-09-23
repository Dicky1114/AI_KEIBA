"""
カスタムバリデーター
"""
import re
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime


def validate_race_date(value):
    """
    レース日付のバリデーション
    過去の日付のみ許可（将来のレースは予測対象）
    """
    if value > timezone.now().date():
        raise ValidationError('レース日付は今日以前の日付を指定してください。')


def validate_horse_name(value):
    """
    馬名のバリデーション
    """
    if len(value) < 2:
        raise ValidationError('馬名は2文字以上で入力してください。')
    
    # 特殊文字をチェック
    if re.search(r'[<>"\']', value):
        raise ValidationError('馬名に使用できない文字が含まれています。')


def validate_jockey_name(value):
    """
    騎手名のバリデーション
    """
    if len(value) < 2:
        raise ValidationError('騎手名は2文字以上で入力してください。')
    
    # 数字のみの名前は不正
    if value.isdigit():
        raise ValidationError('騎手名は数字のみでは登録できません。')


def validate_odds(value):
    """
    オッズのバリデーション
    """
    if value < 1.0:
        raise ValidationError('オッズは1.0以上で入力してください。')
    
    if value > 999.9:
        raise ValidationError('オッズは999.9以下で入力してください。')


def validate_distance(value):
    """
    距離のバリデーション（メートル）
    """
    valid_distances = range(800, 4001, 100)  # 800m〜4000mまで100m刻み
    
    if value not in valid_distances:
        raise ValidationError(
            f'距離は800m〜4000mの範囲で100m刻みで入力してください。入力値: {value}m'
        )


def validate_horse_weight(value):
    """
    馬体重のバリデーション
    """
    if value < 300:
        raise ValidationError('馬体重は300kg以上で入力してください。')
    
    if value > 700:
        raise ValidationError('馬体重は700kg以下で入力してください。')


def validate_jockey_weight(value):
    """
    騎手の斤量バリデーション
    """
    if value < 48.0:
        raise ValidationError('斤量は48.0kg以上で入力してください。')
    
    if value > 65.0:
        raise ValidationError('斤量は65.0kg以下で入力してください。')


def validate_finish_time(value):
    """
    完走タイムのバリデーション
    形式: MM:SS.f (例: 1:23.4)
    """
    time_pattern = r'^\d{1,2}:\d{2}\.\d{1}$'
    
    if not re.match(time_pattern, value):
        raise ValidationError(
            'タイムの形式が正しくありません。MM:SS.f の形式で入力してください。(例: 1:23.4)'
        )
    
    # 時間の妥当性をチェック
    try:
        parts = value.split(':')
        minutes = int(parts[0])
        seconds_parts = parts[1].split('.')
        seconds = int(seconds_parts[0])
        
        if minutes > 10:  # 10分を超えるタイムは異常
            raise ValidationError('タイムが異常です。10分以内で入力してください。')
        
        if seconds >= 60:
            raise ValidationError('秒は60未満で入力してください。')
            
    except (ValueError, IndexError):
        raise ValidationError('タイムの形式が正しくありません。')


def validate_confidence_score(value):
    """
    信頼度スコアのバリデーション
    """
    if not 0.0 <= value <= 1.0:
        raise ValidationError('信頼度スコアは0.0〜1.0の範囲で入力してください。')


def validate_venue_code(value):
    """
    競馬場コードのバリデーション
    """
    valid_codes = [
        '01', '02', '03', '04', '05', '06', '07', '08', '09', '10',  # 中央競馬
        '11', '12', '13', '14', '15', '16', '17', '18', '19', '20',  # 地方競馬（一部）
    ]
    
    if value not in valid_codes:
        raise ValidationError(f'無効な競馬場コードです: {value}')


def validate_race_number(value):
    """
    レース番号のバリデーション
    """
    if not 1 <= value <= 12:
        raise ValidationError('レース番号は1〜12の範囲で入力してください。')


def validate_horse_number(value):
    """
    馬番のバリデーション
    """
    if not 1 <= value <= 18:
        raise ValidationError('馬番は1〜18の範囲で入力してください。')


def validate_frame_number(value):
    """
    枠番のバリデーション
    """
    if not 1 <= value <= 8:
        raise ValidationError('枠番は1〜8の範囲で入力してください。')
