#!/usr/bin/env python3
"""
@file    export_full_report.py
@brief   競馬ML検証の全成果を1つのExcelに集約(8シート・日本語ヘッダー)
@version 1.0.0  2026-06-30  (Dicky1114)

シート構成:
  0. サマリー       — 結論・5つの検証・最終診断
  1. ①生データ      — DBの素データ(サンプル3レース)
  2. ②正規化データ  — 特徴量加工後(80特徴・サンプル)
  3. ③学習直前データ— モデルに渡る直前の行列(エンコード後)
  4. 特徴量カタログ  — 全特徴の日本語名/説明/段階/アブレーション寄与
  5. アブレーション群— 情報群ごとの市場超え寄与(ΔLL)とAUC寄与
  6. アブレーション個— 1特徴ずつの寄与(全81)
  7. 検証方法        — ウォークフォワード各foldの実日付/件数/結果
  8. 回収率          — 券種別バックテスト結果

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/export_full_report.py
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
from scripts.export_pipeline_excel import JP, SAMPLE_RACES, stage1_raw, jp_cols

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 特徴量の説明(日本語)
DESC = {
    'frame_number': '枠番(1-8)', 'sex': '性別(牡牝セ)', 'age': '年齢',
    'weight': '斤量(背負う重量kg)', 'body_weight': '馬体重kg', 'body_weight_diff': '前走比の馬体重増減',
    'odds': '単勝オッズ(市場評価)', 'popularity': '人気順位', 'implied_prob': 'オッズ由来の市場勝率',
    'distance_m': 'レース距離m', 'field_type': '芝/ダート/障害', 'track_condition': '馬場状態(良〜不良)',
    'weather': '天候', 'count': '出走頭数', 'race_place': '競馬場',
    'race_class': 'クラス(新馬〜G1)', 'class_level': 'クラス能力序列(0-8)',
    'prev_class_level': '前走のクラス序列', 'class_drop': '昇降級(前走−今走、+は格下げ=楽)',
    'new_flg': '新馬戦か', 'not_win_flg': '未勝利戦か', 'op_flg': 'オープン戦か',
    'prev_rank': '前走着順', 'prev_popularity': '前走人気', 'prev_last3f': '前走の上がり3F',
    'prev_odds': '前走オッズ', 'days_since_last': '前走からの間隔(日)',
    'avg_rank3': '直近3走平均着順', 'best_rank_prior': '過去最高着順', 'n_runs_prior': '過去出走数',
    'win_rate_prior': '過去勝率', 'place_rate_prior': '過去複勝率',
    'j_runs_prior': '騎手の過去騎乗数', 'j_win_rate_prior': '騎手勝率', 'j_place_rate_prior': '騎手複勝率',
    't_runs_prior': '調教師の過去出走数', 't_win_rate_prior': '調教師勝率', 't_place_rate_prior': '調教師複勝率',
    'prev_speed': '前走スピード指数', 'avg_speed3': '直近3走平均スピード指数', 'best_speed': '過去最高スピード指数',
    'prev2_speed': '前々走スピード指数', 'speed_trend': 'スピード傾向(前走−前々走)', 'speed_momentum': '直近が平均より上か',
    'oikiri_grade': '調教評価(S/A/B→数値)', 'oikiri_sentiment': '調教コメントの良し悪し',
    'prev_early_pos': '前走の位置取り(0先頭1後方)', 'avg_early_pos3': '直近3走平均位置取り',
    'sire': '父(種牡馬)', 'sire_win_rate': '父産駒の勝率', 'broodmare_sire': '母父',
    'sire_te': '父のターゲットエンコード(産駒勝率平滑化)', 'bms_te': '母父のターゲットエンコード',
    'prev_last3f_rank': '前走の上がり3F順位', 'avg_last3f_rank3': '直近3走平均上がり順位',
    'prev2_rank': '前々走着順', 'rank_trend': '着順傾向(良化/悪化)',
    'rel_prev_speed': 'レース内相対_前走スピード', 'rel_avg_speed3': 'レース内相対_平均スピード',
    'rel_avg_rank3': 'レース内相対_平均着順', 'rel_last3f_rank': 'レース内相対_上がり順位',
    'ft_runs': '同芝ダでの過去出走数', 'ft_winrate': '同芝ダでの過去勝率',
    'ft_placerate': '同芝ダでの過去複勝率', 'ft_avgspeed': '同芝ダでの平均スピード指数',
    'dist_runs': '同距離帯での過去出走数', 'dist_winrate': '同距離帯での過去勝率',
    'dist_placerate': '同距離帯での過去複勝率', 'dist_avgspeed': '同距離帯での平均スピード指数',
    'course_runs': '同コースでの過去出走数', 'course_winrate': '同コースでの過去勝率',
    'course_placerate': '同コースでの過去複勝率', 'course_avgspeed': '同コースでの平均スピード指数',
    'layoff_long': '休み明け(90日以上)', 'layoff_short': '連闘・詰め(14日以内)',
    'frame_ratio': '枠/頭数(外枠不利の代理)', 'post_ratio': '馬番/頭数',
    'weight_ratio': '斤量/馬体重(負担率)', 'ix_going_pos': '道悪×脚質', 'ix_dist_pos': '距離×脚質',
    'pace_pressure': 'レース内の先行馬頭数(展開)', 'style_x_pace': '自分の脚質×展開',
    'ix_pos_dist': '脚質×距離(交互作用)',
}
# 特徴→情報群
GROUP_OF = {}
_GROUPS = {
    '市場': ['odds', 'popularity', 'implied_prob'],
    'クラス': ['race_class', 'class_level', 'prev_class_level', 'class_drop', 'new_flg', 'not_win_flg', 'op_flg'],
    '血統': ['sire', 'sire_win_rate', 'broodmare_sire', 'sire_te', 'bms_te'],
    '調教': ['oikiri_grade', 'oikiri_sentiment'],
    'スピード指数': ['prev_speed', 'avg_speed3', 'best_speed', 'prev2_speed', 'speed_trend', 'speed_momentum'],
    '過去成績': ['prev_rank', 'avg_rank3', 'best_rank_prior', 'n_runs_prior', 'win_rate_prior',
             'place_rate_prior', 'prev2_rank', 'rank_trend', 'prev_popularity', 'prev_odds'],
    '条件別適性': ['ft_runs', 'ft_winrate', 'ft_placerate', 'ft_avgspeed', 'dist_runs', 'dist_winrate',
               'dist_placerate', 'dist_avgspeed', 'course_runs', 'course_winrate', 'course_placerate', 'course_avgspeed'],
    '騎手': ['j_runs_prior', 'j_win_rate_prior', 'j_place_rate_prior'],
    '調教師': ['t_runs_prior', 't_win_rate_prior', 't_place_rate_prior'],
    '脚質/展開': ['prev_early_pos', 'avg_early_pos3', 'pace_pressure', 'style_x_pace', 'ix_going_pos', 'ix_dist_pos', 'ix_pos_dist'],
    '末脚3F': ['prev_last3f', 'prev_last3f_rank', 'avg_last3f_rank3'],
    '馬体/斤量': ['body_weight', 'body_weight_diff', 'weight', 'weight_ratio'],
    '枠/休養': ['frame_number', 'frame_ratio', 'post_ratio', 'days_since_last', 'layoff_long', 'layoff_short'],
    'レース内相対': ['rel_prev_speed', 'rel_avg_speed3', 'rel_avg_rank3', 'rel_last3f_rank'],
    '基本': ['sex', 'age', 'distance_m', 'field_type', 'track_condition', 'weather', 'count', 'race_place'],
}
for grp, cols in _GROUPS.items():
    for c in cols:
        GROUP_OF[c] = grp

# 分析結果(検証済みの実測値を埋め込み)
SUMMARY = [
    ['競馬予測 ローカルパイプライン 検証総括', ''],
    ['', ''],
    ['データ', '2562レース / 35865行 / 2025-10-04〜2026-06-28(約9ヶ月)'],
    ['特徴量', '80(市場/クラス/血統/調教/スピード指数/条件別適性/騎手/調教師/脚質展開/末脚/馬体/枠休養/相対)'],
    ['モデル', 'LightGBM(二値勝率) + 市場ブレンド(Benter式α·logf+β·logπ)'],
    ['検証法', '時系列ウォークフォワード5fold(過去で学習→未来でテスト・リーク防止)'],
    ['', ''],
    ['◆ 5つの角度の検証結果', ''],
    ['1. スコア絞り込み', '単一split 114% → ウォークフォワード 79%(上振れの幻)'],
    ['2. 券種別・価値意識の買い方', '最良=複勝90% / 100%超は0/5fold(安定して勝てる買い方なし)'],
    ['3. 前処理改善(カテゴリ/NaN/TE)', 'ΔLL +0.003で不変・AUCはむしろ漏れが取れて正直化'],
    ['4. 研究反映80特徴(条件別適性等)', 'ΔLL +0.003で不変(新特徴も市場超えに寄与せず)'],
    ['5. アブレーション(群+個別)', '市場を超える寄与を持つ特徴は群でも個別でも皆無'],
    ['', ''],
    ['◆ 核心(市場効率の証拠)', ''],
    ['オッズの逆説', 'オッズを抜くとAUC −0.052(最強予測子)なのにΔLL寄与 −0.0001。理由=オッズ=市場そのもの'],
    ['血統の過学習', '父系を抜くとAUC改善(+0.0147)=父812種を暗記するノイズ'],
    ['必要ΔLL水準', '市場超えには0.01〜0.02必要(Benter実証)。当方は+0.003でσ内=ゼロと区別不能'],
    ['', ''],
    ['◆ 最終診断', 'データ・前処理・特徴量・検証を研究水準で正しく実装しても、現状の公開JRAデータでは'],
    ['', '市場(オッズ)に勝てない。ボトルネックは情報が全て市場価格に織込済(効率的市場)。'],
    ['', '利益目的なら到達点。割り切り=損最小の複勝本命1点(回収90%/的中77%)か予測精度を楽しむツール化。'],
]
GROUP_ABLATION = [  # (群, ΔLL寄与, AUC寄与, 判定)
    ('調教師', 0.0004, 0.0007, '中立(ノイズ内)'), ('血統', 0.0002, -0.0147, '中立/AUCは過学習'),
    ('基本属性', 0.0001, -0.0003, '中立'), ('過去着順/勝率', 0.0001, -0.0002, '中立'),
    ('スピード指数', 0.0000, 0.0002, '中立'), ('条件別適性', -0.0000, 0.0004, '中立(市場超え寄与ゼロ)'),
    ('騎手', -0.0001, 0.0010, '中立'), ('市場(odds/人気)', -0.0001, 0.0520, 'AUC最重要だが市場超え寄与なし'),
    ('枠/休養', -0.0001, -0.0011, '中立'), ('クラス', -0.0002, -0.0001, '中立'),
    ('脚質/展開', -0.0002, -0.0001, '中立'), ('レース内相対', -0.0002, 0.0006, '中立'),
    ('末脚3F', -0.0002, 0.0003, '中立'), ('馬体/斤量', -0.0004, 0.0003, '削除候補'),
    ('調教', -0.0007, -0.0007, '削除候補(抜く方が良い)'),
]
VALIDATION = [  # fold, 学習期間, 学習R, テスト期間, テストR, 学習秒, 木数, AUC, ΔLL
    (1, '2025-10-04〜2026-02-15', 1281, '02-15〜03-15', 256, 3.3, 600, 0.798, 0.0045),
    (2, '〜2026-03-15', 1537, '03-15〜04-12', 256, 3.7, 600, 0.802, 0.0051),
    (3, '〜2026-04-12', 1793, '04-12〜05-09', 256, 3.3, 600, 0.792, 0.0021),
    (4, '〜2026-05-09', 2049, '05-09〜06-06', 256, 3.3, 600, 0.831, 0.0028),
    (5, '〜2026-06-06', 2305, '06-06〜06-28', 257, 3.5, 600, 0.820, 0.0016),
]
BETTING = [  # 戦略, 平均ROI%, σ, >100fold, 購入R, 的中率%
    ('複勝_本命1点(c>=.30)', 90, 2, '0/5', 847, 77.1), ('複勝_本命厚(c>=.40)', 89, 2, '0/5', 373, 80.7),
    ('複勝_top2(c>=.30)', 88, 3, '0/5', 847, 91.6), ('馬連_本命軸-妙味流し', 82, 6, '0/5', 1318, 29.1),
    ('3連複_本命軸-相手流し', 82, 8, '0/5', 1318, 44.8), ('3連複_top4BOX_妙味込', 80, 4, '0/5', 1518, 24.2),
    ('単勝_本命のみ', 78, 3, '0/5', 561, 44.2), ('3連単_本命1着固定-妙味流し', 65, 7, '0/5', 1318, 16.5),
]


def feature_catalog():
    abl = pd.read_csv(os.path.join(BASE_DIR, 'media', 'csv_export', 'ablation_result.csv'))
    abl = abl.set_index('feature')
    rows = []
    for f in DESC:
        dll = abl['dll_contrib'].get(f, np.nan)
        auc = abl['auc_contrib'].get(f, np.nan)
        verdict = ''
        if pd.notna(dll):
            verdict = '効く(僅)' if dll > 0.0002 else ('削除候補' if dll < -0.0005 else '中立')
        rows.append({'特徴量': f, '日本語名': JP.get(f, f), '説明': DESC.get(f, ''),
                     '情報群': GROUP_OF.get(f, '-'),
                     'ΔLL寄与(市場超え)': round(dll, 5) if pd.notna(dll) else None,
                     'AUC寄与(予測精度)': round(auc, 5) if pd.notna(auc) else None,
                     '判定': verdict})
    return pd.DataFrame(rows)


def main():
    df = load_data(); df['race_id'] = df['race_id'].astype(str)
    sel = df[df['race_id'].isin(SAMPLE_RACES)].copy().sort_values(['race_id', 'horse_number'])

    raw = stage1_raw()
    norm = sel.copy()
    X, y, info = improved_prepare(df, np.ones(len(df), bool))
    cats = info[0]
    Xsel = X.loc[sel.index].copy()
    for c in cats:
        if str(Xsel[c].dtype) == 'category':
            Xsel[c] = [f"{cd} ({lb})" for cd, lb in zip(Xsel[c].cat.codes, Xsel[c].astype(str))]
    Xsel.insert(0, 'race_id', sel['race_id'].values)
    Xsel.insert(1, 'horse_number', sel['horse_number'].values)
    Xsel.insert(2, 'is_win', y.loc[sel.index].values)

    out = os.path.join(BASE_DIR, 'media', 'csv_export', 'keiba_full_report.xlsx')
    with pd.ExcelWriter(out, engine='openpyxl') as xw:
        pd.DataFrame(SUMMARY, columns=['項目', '内容']).to_excel(xw, '0_サマリー', index=False)
        jp_cols(raw).to_excel(xw, '1_生データ', index=False)
        jp_cols(norm).to_excel(xw, '2_正規化データ', index=False)
        jp_cols(Xsel).to_excel(xw, '3_学習直前データ', index=False)
        feature_catalog().to_excel(xw, '4_特徴量カタログ', index=False)
        pd.DataFrame(GROUP_ABLATION, columns=['情報群', 'ΔLL寄与(市場超え)', 'AUC寄与(予測精度)', '判定']
                     ).to_excel(xw, '5_アブレーション群別', index=False)
        abl = pd.read_csv(os.path.join(BASE_DIR, 'media', 'csv_export', 'ablation_result.csv'))
        abl['日本語名'] = abl['feature'].map(lambda f: JP.get(f, f))
        abl['情報群'] = abl['feature'].map(lambda f: GROUP_OF.get(f, '-'))
        abl = abl[['feature', '日本語名', '情報群', 'dll_contrib', 'auc_contrib']]
        abl.columns = ['特徴量', '日本語名', '情報群', 'ΔLL寄与(市場超え)', 'AUC寄与(予測精度)']
        abl.sort_values('ΔLL寄与(市場超え)', ascending=False).to_excel(xw, '6_アブレーション個別', index=False)
        pd.DataFrame(VALIDATION, columns=['fold', '学習期間', '学習R', 'テスト期間', 'テストR',
                     '学習秒', '木数', 'AUC', 'ΔLL']).to_excel(xw, '7_検証方法', index=False)
        pd.DataFrame(BETTING, columns=['戦略', '平均回収率%', 'σ', '>100%fold', '購入R', '的中率%']
                     ).to_excel(xw, '8_回収率', index=False)
        from openpyxl.utils import get_column_letter
        for ws in xw.book.worksheets:
            for i, col in enumerate(ws.columns, 1):
                w = max((len(str(c.value)) for c in col if c.value is not None), default=10)
                ws.column_dimensions[get_column_letter(i)].width = min(max(w + 1, 10), 40)
            ws.freeze_panes = 'A2'
    logger.info(f"出力: {out}")
    print(f"DONE {out}")


if __name__ == '__main__':
    main()
