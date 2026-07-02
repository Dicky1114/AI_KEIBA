#!/usr/bin/env python3
"""
@file    export_pipeline_excel.py
@brief   データ3段階(生→正規化→学習直前)を1つのExcelに3シートで出力(日本語ヘッダー)
@version 1.0.0  2026-06-30  (Dicky1114)

3段階の意味:
  ① 生データ        : スクレイプしてDBに入れた素のレース結果(t_base_info+t_result_info)
  ② 正規化データ    : 特徴量エンジニアリング後の学習CSV(スピード指数・各種率・相対値など人が読める数値)
  ③ 学習直前データ  : モデルに渡す直前の行列(カテゴリ→コード化, 欠損NaN, target encoding, 死列除去後)

同じ3レースの同じ馬を3シート通して追えるようにする。

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/export_pipeline_excel.py
"""
import os, sys, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import django  # noqa
django.setup()
from django.db import connection
from scripts.run_roi_analysis import load_data
from scripts.fe_experiment import improved_prepare

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SAMPLE_RACES = ['202602010610', '202603020211', '202610020206']  # 函館/福島/小倉

# 日本語ヘッダー辞書(全ステージ共通)
JP = {
    'race_id': 'レースID', 'race_date': '開催日', 'today_race_date': '開催日',
    'race_place': '競馬場', 'horse_number': '馬番', 'frame_number': '枠番',
    'horse_name': '馬名', 'sex': '性別', 'age': '年齢', 'weight': '斤量(kg)',
    'body_weight': '馬体重(kg)', 'body_weight_diff': '馬体重増減',
    'odds': '単勝オッズ', 'popularity': '人気', 'implied_prob': '市場勝率(1/オッズ)',
    'distance_m': '距離(m)', 'field_type': '芝ダ障', 'track_condition': '馬場状態',
    'weather': '天候', 'count': '出走頭数',
    'rank': '着順', 'race_time': '走破タイム', 'corner_order': '通過順',
    'last_3f': '上がり3F', 'margin': '着差', 'target_time': '目標タイム',
    'pay1': '単勝払戻', 'pay1_tie': '単勝同着', 'pay123_1': '複勝払戻(1着)',
    'pay123_2': '複勝払戻(2着)', 'pay123_3': '複勝払戻(3着)',
    'pay12_21': '馬連払戻', 'pay12_12': '馬単払戻',
    'pay123_321': '3連複払戻', 'pay123_123': '3連単払戻',
    # クラス/属性フラグ
    'new_flg': '新馬戦', 'not_win_flg': '未勝利', 'win_1_flg': '1勝クラス',
    'win_2_flg': '2勝クラス', 'win_3_flg': '3勝クラス', 'g1_flg': 'G1',
    'g2_flg': 'G2', 'g3_flg': 'G3', 'l_flg': 'リステッド', 'op_flg': 'オープン',
    # 過去成績
    'prev_rank': '前走着順', 'prev_popularity': '前走人気', 'prev_last3f': '前走上がり3F',
    'prev_odds': '前走オッズ', 'days_since_last': '中何日', 'avg_rank3': '直近3走平均着順',
    'best_rank_prior': '過去最高着順', 'n_runs_prior': '過去出走数',
    'win_rate_prior': '過去勝率', 'place_rate_prior': '過去複勝率',
    'prev_rank_int': '前走着順',
    # 騎手・調教師
    'j_runs_prior': '騎手出走数', 'j_win_rate_prior': '騎手勝率',
    'j_place_rate_prior': '騎手複勝率', 't_runs_prior': '調教師出走数',
    't_win_rate_prior': '調教師勝率', 't_place_rate_prior': '調教師複勝率',
    # スピード指数・脚質
    'prev_speed': '前走スピード指数', 'avg_speed3': '直近3走平均スピード指数',
    'best_speed': '過去最高スピード指数', 'prev2_speed': '前々走スピード指数',
    'speed_trend': 'スピード傾向', 'speed_momentum': 'スピード勢い',
    'prev_early_pos': '前走位置取り', 'avg_early_pos3': '直近3走平均位置取り',
    'prev_last3f_rank': '前走上がり順位', 'avg_last3f_rank3': '直近3走平均上がり順位',
    'prev2_rank': '前々走着順', 'rank_trend': '着順傾向',
    # 血統・調教
    'sire': '父', 'sire_win_rate': '父産駒勝率', 'broodmare_sire': '母父',
    'oikiri_grade': '調教評価', 'oikiri_sentiment': '調教ニュアンス',
    'sire_te': '父ターゲットエンコード', 'bms_te': '母父ターゲットエンコード',
    # レース内相対
    'rel_prev_speed': 'レース内相対_前走スピード', 'rel_avg_speed3': 'レース内相対_平均スピード',
    'rel_avg_rank3': 'レース内相対_平均着順', 'rel_last3f_rank': 'レース内相対_上がり順位',
    # 交互作用(改善版で追加)
    'ix_pos_dist': '交互_脚質×距離', 'ix_going_pos': '交互_道悪×脚質',
    'frame_ratio': '枠順比率', 'weight_ratio': '斤量/馬体重比',
    'is_win': '勝ち(1=1着)',
}


def jp_cols(df):
    return df.rename(columns={c: JP.get(c, c) for c in df.columns})


def stage1_raw():
    """① 生データ: DBのt_base_info + t_result_info を素のまま結合。"""
    ids = "','".join(SAMPLE_RACES)
    sql = f"""
      SELECT b.race_id, b.race_date, b.race_place, b.horse_number, r.horse_name,
             b.sex, b.age, b.weight, b.body_weight, b.body_weight_diff,
             b.odds, b.popularity, b.distance_m, b.field_type, b.track_condition,
             b.weather, b.count,
             r.rank, r.race_time, r.corner_order, r.last_3f, r.margin,
             r.pay1, r.pay123_1, r.pay123_2, r.pay123_3,
             r.pay12_21, r.pay12_12, r.pay123_321, r.pay123_123
      FROM t_base_info b
      LEFT JOIN t_result_info r ON b.race_id=r.race_id AND b.horse_number=r.horse_number
      WHERE b.race_id IN ('{ids}')
      ORDER BY b.race_id, b.horse_number
    """
    return pd.read_sql(sql, connection)


def main():
    df = load_data()
    df['race_id'] = df['race_id'].astype(str)
    sel = df[df['race_id'].isin(SAMPLE_RACES)].copy().sort_values(['race_id', 'horse_number'])
    logger.info(f"サンプル {len(sel)}行 / {sel['race_id'].nunique()}レース")

    # ① 生データ
    raw = stage1_raw()

    # ② 正規化データ(学習CSVの該当行・読みやすい派生特徴)
    norm = sel.copy()

    # ③ 学習直前データ(改善版前処理で実際にモデルへ渡る行列)
    tr_mask = np.ones(len(df), dtype=bool)  # 表示用: 全体でtarget-enc(本番は学習区間のみ)
    X, y, info = improved_prepare(df, tr_mask)
    cats, dead = info
    Xsel = X.loc[sel.index].copy()
    # カテゴリ列は「モデルが見るコード」に変換して表示(元ラベルも括弧で)
    for c in cats:
        if str(Xsel[c].dtype) == 'category':
            codes = Xsel[c].cat.codes
            labels = Xsel[c].astype(str)
            Xsel[c] = [f"{cd} ({lb})" for cd, lb in zip(codes, labels)]
    Xsel.insert(0, 'race_id', sel['race_id'].values)
    Xsel.insert(1, 'horse_number', sel['horse_number'].values)
    Xsel.insert(2, 'is_win', y.loc[sel.index].values)

    out = os.path.join(BASE_DIR, 'media', 'csv_export', 'keiba_pipeline_3stages.xlsx')
    with pd.ExcelWriter(out, engine='openpyxl') as xw:
        jp_cols(raw).to_excel(xw, sheet_name='①生データ', index=False)
        jp_cols(norm).to_excel(xw, sheet_name='②正規化データ', index=False)
        jp_cols(Xsel).to_excel(xw, sheet_name='③学習直前データ', index=False)
        # 列幅自動
        from openpyxl.utils import get_column_letter
        for ws in xw.book.worksheets:
            for i, col in enumerate(ws.columns, 1):
                w = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                ws.column_dimensions[get_column_letter(i)].width = min(max(w + 1, 8), 22)
            ws.freeze_panes = 'C2'

    logger.info(f"出力: {out}")
    logger.info(f"削除した死列(学習区間でuniq<=1): {dead}")
    logger.info(f"カテゴリ宣言した列: {cats}")
    print(f"\nDONE {out}")
    print(f"  ①生データ {raw.shape}  ②正規化 {norm.shape}  ③学習直前 {Xsel.shape}")
    print(f"  死列削除: {dead}")
    print(f"  カテゴリ列: {cats}")


if __name__ == '__main__':
    main()
