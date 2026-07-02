#!/usr/bin/env python3
"""
@file    ablation.py
@brief   アブレーション分析: 全特徴を入れて1個ずつ(&グループごと)抜き、各特徴の寄与を測る
@version 1.0.0  2026-06-30  (Dicky1114)

ユーザー方針: 「全データ入れて、非オッズを1個ずつ無くして検証し、精度がどれだけ変わるか、
              どの項目がどれだけ影響するかを見て、効く項目だけ残す/作る」=正攻法のアブレーション。

測る指標(2つ):
  ・ΔLL : 市場ブレンド後の対数尤度改善(賭けで勝てるか=本命指標)
  ・AUC : 順位予測の良さ(参考。市場と同じ情報でも上がる)
寄与 = (全部入り) − (その特徴を抜いた版)。正なら「その特徴が効いている」。
       負(抜いた方が良い)なら「ノイズ/市場コピー」=削除候補。

2段階:
  (1) グループ別アブレーション: 相関する特徴を束ねて抜く(LOOの過小評価を回避・全体像把握)
  (2) 個別アブレーション: 1特徴ずつ抜く(ユーザー指定の粒度)
時系列ウォークフォワード(過去→未来)で N_FOLDS 評価し平均±σ。

使用(時間がかかるのでバックグラウンド推奨):
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/ablation.py
"""
import os, sys, time, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import django  # noqa
django.setup()
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from scripts.run_roi_analysis import load_data
from scripts.fe_experiment import improved_prepare, winner_ll

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
N_FOLDS = 4
N_TREES = 400

# グループ定義(相関する特徴の束)
GROUPS = {
    '市場(odds/人気)': ['odds', 'popularity', 'implied_prob'],
    'クラス': ['race_class', 'class_level', 'prev_class_level', 'class_drop'],
    '血統': ['sire', 'sire_win_rate', 'broodmare_sire', 'sire_te', 'bms_te'],
    '調教': ['oikiri_grade', 'oikiri_sentiment'],
    'スピード指数': ['prev_speed', 'avg_speed3', 'best_speed', 'prev2_speed',
                 'speed_trend', 'speed_momentum'],
    '過去着順/勝率': ['prev_rank', 'avg_rank3', 'best_rank_prior', 'n_runs_prior',
                 'win_rate_prior', 'place_rate_prior', 'prev2_rank', 'rank_trend'],
    '条件別適性': ['ft_runs', 'ft_winrate', 'ft_placerate', 'ft_avgspeed',
               'dist_runs', 'dist_winrate', 'dist_placerate', 'dist_avgspeed',
               'course_runs', 'course_winrate', 'course_placerate', 'course_avgspeed'],
    '騎手': ['j_runs_prior', 'j_win_rate_prior', 'j_place_rate_prior'],
    '調教師': ['t_runs_prior', 't_win_rate_prior', 't_place_rate_prior'],
    '脚質/展開': ['prev_early_pos', 'avg_early_pos3', 'pace_pressure', 'style_x_pace',
              'ix_going_pos', 'ix_dist_pos'],
    '末脚3F': ['prev_last3f', 'prev_last3f_rank', 'avg_last3f_rank3'],
    '馬体/斤量': ['body_weight', 'body_weight_diff', 'weight', 'weight_ratio'],
    '枠/休養': ['frame_number', 'frame_ratio', 'post_ratio', 'days_since_last',
             'layoff_long', 'layoff_short'],
    'レース内相対': ['rel_prev_speed', 'rel_avg_speed3', 'rel_avg_rank3', 'rel_last3f_rank'],
    '基本属性': ['sex', 'age', 'distance_m', 'field_type', 'track_condition',
             'weather', 'count', 'race_place', 'new_flg', 'not_win_flg', 'op_flg'],
}


def eval_feature_set(df, drop_cols, label=''):
    """drop_cols を除いてウォークフォワード学習し、ΔLL平均/AUC平均を返す。"""
    races = (df[['today_race_date', 'race_id']].drop_duplicates()
             .sort_values(['today_race_date', 'race_id'])['race_id'].tolist())
    n = len(races); start = n // 2; block = (n - start) // N_FOLDS
    dlls, aucs = [], []
    for k in range(N_FOLDS):
        te_lo = start + k * block; te_hi = start + (k + 1) * block if k < N_FOLDS - 1 else n
        test_ids = set(races[te_lo:te_hi]); train_ids = set(races[:te_lo])
        tr = df['race_id'].isin(train_ids).values; te = df['race_id'].isin(test_ids).values
        X, y, info = improved_prepare(df, tr)
        cats = [c for c in info[0] if c in X.columns and c not in drop_cols]
        keep = [c for c in X.columns if c not in drop_cols]
        clf = lgb.LGBMClassifier(objective='binary', n_estimators=N_TREES, learning_rate=0.03,
                                 num_leaves=31, max_depth=5, min_child_samples=30, subsample=0.8,
                                 colsample_bytree=0.8, reg_lambda=5.0, random_state=42, n_jobs=-1, verbosity=-1)
        clf.fit(X[keep][tr], y[tr], categorical_feature=cats)
        p = clf.predict_proba(X[keep][te])[:, 1]
        aucs.append(roc_auc_score(y[te], p))
        dt = df[te].copy(); dt['p'] = p
        ll_mkt, blend = winner_ll(dt, 'p', use_blend=True)
        dlls.append(ll_mkt - blend[0])
    return np.mean(dlls), np.std(dlls), np.mean(aucs)


def main():
    df = load_data()
    logger.info(f"{len(df)}行 / {df['race_id'].nunique()}レース / {N_FOLDS}fold / {N_TREES}本")

    # 全部入りベースライン
    t0 = time.time()
    base_dll, base_dll_sd, base_auc = eval_feature_set(df, set(), '全部入り')
    logger.info(f"[基準] 全部入り ΔLL={base_dll:+.4f}±{base_dll_sd:.4f} AUC={base_auc:.4f} ({time.time()-t0:.0f}s)")

    # (1) グループ別アブレーション
    print("\n" + "=" * 90)
    print("  (1) グループ別アブレーション: そのグループを抜くとΔLL/AUCがどう変わるか")
    print(f"      基準(全部入り): ΔLL={base_dll:+.4f}  AUC={base_auc:.4f}")
    print("=" * 90)
    print(f"  {'抜いたグループ':18}{'ΔLL':>9}{'ΔLL寄与':>9}{'AUC':>8}{'AUC寄与':>9}  {'判定':<12}")
    print("  " + "-" * 84)
    grp_rows = []
    for name, cols in GROUPS.items():
        dll, sd, auc = eval_feature_set(df, set(cols))
        c_dll = base_dll - dll; c_auc = base_auc - auc
        verdict = '★効く' if c_dll > 0.0010 else ('ノイズ?' if c_dll < -0.0005 else '中立')
        grp_rows.append((name, dll, c_dll, auc, c_auc, verdict))
    for name, dll, c_dll, auc, c_auc, v in sorted(grp_rows, key=lambda x: -x[2]):
        print(f"  {name:18}{dll:>+9.4f}{c_dll:>+9.4f}{auc:>8.4f}{c_auc:>+9.4f}  {v:<12}")
    print("=" * 90)

    # (2) 個別アブレーション(1特徴ずつ・ユーザー指定の粒度)
    X0, _, info0 = improved_prepare(df, np.ones(len(df), bool))
    all_feats = [c for c in X0.columns]
    print("\n" + "=" * 90)
    print(f"  (2) 個別アブレーション: 1特徴ずつ抜く({len(all_feats)}特徴)")
    print("=" * 90)
    rows = []
    for i, f in enumerate(all_feats):
        dll, sd, auc = eval_feature_set(df, {f})
        rows.append((f, base_dll - dll, base_auc - auc))
        if (i + 1) % 10 == 0:
            logger.info(f"  ...{i+1}/{len(all_feats)} 完了")
    rows.sort(key=lambda x: -x[1])
    print(f"  {'特徴量':24}{'ΔLL寄与':>10}{'AUC寄与':>10}")
    print("  " + "-" * 46)
    print("  --- ΔLL寄与 上位15(賭けに効く) ---")
    for f, cd, ca in rows[:15]:
        print(f"  {f:24}{cd:>+10.4f}{ca:>+10.4f}")
    print("  --- ΔLL寄与 下位10(抜いた方が良い=削除候補) ---")
    for f, cd, ca in rows[-10:]:
        print(f"  {f:24}{cd:>+10.4f}{ca:>+10.4f}")
    print("=" * 90)
    out = os.path.join(BASE_DIR, 'media', 'csv_export', 'ablation_result.csv')
    pd.DataFrame(rows, columns=['feature', 'dll_contrib', 'auc_contrib']).to_csv(out, index=False)
    print(f"  全結果CSV: {out}")
    print("  注: 相関の強い特徴は単独LOOだと寄与が過小に出る(他が代替)。グループ別と併読のこと。")


if __name__ == '__main__':
    main()
