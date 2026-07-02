#!/usr/bin/env python3
"""
@file    fe_experiment.py
@brief   前処理/特徴量エンジニアリングの改善が「市場超え指標ΔLL」を動かすか検証
@version 1.0.0  2026-06-30  (Dicky1114)

検証する改善(現 build_xy: cat.codes + fillna(-1) + カテゴリ未宣言 がベースライン):
  FIX1 死列削除      : 全行同値(uniq<=1)の列を捨てる(win_x_flg/g_x_flg等)
  FIX2 カテゴリ宣言   : sex/field_type/weather/race_place/sire/broodmare_sire を
                       LightGBM categorical_feature として渡す(順序数扱いをやめる)
  FIX3 NaNネイティブ : fillna(-1) をやめ NaN のまま渡す(LightGBMが分岐で扱う)
  FIX4 母父target-enc: broodmare_sire を 学習区間の勝率で target encoding(リーク防止CV)
  FIX5 交互作用      : 脚質×距離, 馬場状態×脚質, 枠順/頭数 等の素直な交差

判定:
  ・winner logloss(低いほど良) と AUC を baseline vs improved で比較
  ・**ΔLL = LL(市場単独) - LL(モデル+市場ブレンド)**。正なら市場に無い情報を足せている。
    複数foldで平均>0 かつ σ内で安定して+なら「効いた」。0近傍なら前処理を直しても
    市場効率の壁は越えない=精度問題でなく情報問題、が確定。

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/fe_experiment.py
"""
import os, sys, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import django  # noqa
django.setup()
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, log_loss
from scripts.run_roi_analysis import load_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

LEAK = {'rank', 'target_time', 'race_time', 'corner_order', 'last_3f', 'margin',
        'pay1', 'pay123_1', 'pay123_2', 'pay123_3', 'pay12_12', 'pay12_21',
        'pay123_123', 'pay123_321', 'positions', 'positions_tie', 'pay1_tie',
        'pay123_tie', 'is_win', 'win_label'}
KEYS = {'today_race_date', 'race_id', 'horse_number', 'id'}
CAT_COLS = ['sex', 'field_type', 'weather', 'race_place', 'frame_number',
            'oikiri_grade', 'race_class']


def base_prepare(df):
    """現行 build_xy 相当(ベースライン): cat.codes + fillna(-1), カテゴリ未宣言。"""
    d = df.copy()
    d['is_win'] = (pd.to_numeric(d['rank'], errors='coerce') == 1).astype(int)
    feat = [c for c in d.columns if c not in (LEAK | KEYS)]
    X = d[feat].copy()
    for c in X.columns:
        if X[c].dtype == 'object':
            X[c] = X[c].astype('category').cat.codes
        else:
            X[c] = pd.to_numeric(X[c], errors='coerce')
    X = X.fillna(-1).astype('float32')
    return X, d['is_win'], None


def improved_prepare(df, train_mask):
    """改善版: 死列削除 / カテゴリ宣言 / NaN native / 母父target-enc / 交互作用。"""
    d = df.copy()
    d['is_win'] = (pd.to_numeric(d['rank'], errors='coerce') == 1).astype(int)

    # FIX5 交互作用(数値化前に作る)
    d['sex'] = d['sex'].astype(str)
    d['field_type'] = d['field_type'].astype(str)
    d['track_condition'] = d['track_condition'].astype(str)
    # 脚質×距離
    d['ix_pos_dist'] = pd.to_numeric(d['avg_early_pos3'], errors='coerce') * pd.to_numeric(d['distance_m'], errors='coerce')
    # 馬場状態×脚質(良/重 で先行有利が変わる)
    d['ix_going_pos'] = (d['track_condition'].isin(['重', '不良']).astype(int)
                         * pd.to_numeric(d['avg_early_pos3'], errors='coerce'))
    # 枠順比率(頭数で正規化=外枠不利の代理)
    d['frame_ratio'] = pd.to_numeric(d['frame_number'], errors='coerce') / pd.to_numeric(d['count'], errors='coerce')
    # 斤量/馬体重(負担比)
    d['weight_ratio'] = pd.to_numeric(d['weight'], errors='coerce') / pd.to_numeric(d['body_weight'], errors='coerce')

    # FIX4 母父 target encoding(学習区間のみで勝率→写像。未知は全体平均)
    d['broodmare_sire'] = (d['broodmare_sire'].astype(str)
                           .str.split().str[0])  # 表記揺れ吸収(先頭トークン)
    tr = d[train_mask]
    gmean = tr['is_win'].mean()
    enc = tr.groupby('broodmare_sire')['is_win'].agg(['mean', 'count'])
    # スムージング(count小はgmeanへ寄せる)
    m = 20
    enc['te'] = (enc['mean'] * enc['count'] + gmean * m) / (enc['count'] + m)
    d['bms_te'] = d['broodmare_sire'].map(enc['te']).fillna(gmean).astype('float32')
    # sire も同様
    d['sire'] = d['sire'].astype(str).str.split().str[0]
    encs = tr.groupby('sire')['is_win'].agg(['mean', 'count'])
    encs['te'] = (encs['mean'] * encs['count'] + gmean * m) / (encs['count'] + m)
    d['sire_te'] = d['sire'].map(encs['te']).fillna(gmean).astype('float32')

    drop = set(LEAK | KEYS | {'broodmare_sire', 'sire'})
    feat = [c for c in d.columns if c not in drop]
    # FIX1 死列削除(学習区間で uniq<=1)
    dead = [c for c in feat if d.loc[train_mask, c].nunique(dropna=True) <= 1]
    feat = [c for c in feat if c not in dead]

    X = d[feat].copy()
    cats = []
    for c in X.columns:
        if c in CAT_COLS or X[c].dtype == 'object' or X[c].dtype == 'bool':
            X[c] = X[c].astype('category')         # FIX2 カテゴリ宣言(NaNはそのまま)
            cats.append(c)
        else:
            X[c] = pd.to_numeric(X[c], errors='coerce').astype('float32')  # FIX3 NaN native
    return X, d['is_win'], (cats, dead)


def winner_ll(df_test, p_model_col, use_blend=True):
    """レース内 winner の対数尤度。市場π=1/odds正規化。blend=α·logf+β·logπ をfit。"""
    from scipy.optimize import minimize
    d = df_test.copy()
    d['odds'] = pd.to_numeric(d['odds'], errors='coerce')
    d = d[d['odds'] > 0]
    d['pi'] = d.groupby('race_id')['odds'].transform(lambda o: (1 / o) / (1 / o).sum())
    d['f'] = d.groupby('race_id')[p_model_col].transform(lambda s: s / s.sum() if s.sum() > 0 else s)
    d['y'] = (pd.to_numeric(d['rank'], errors='coerce') == 1).astype(int)
    eps = 1e-9
    lf = np.log(np.clip(d['f'].values, eps, 1)); lp = np.log(np.clip(d['pi'].values, eps, 1))
    rid = d['race_id'].values; y = d['y'].values

    def race_ll(c):
        d2 = d.assign(_c=c)
        s = d2.groupby('race_id')['_c'].transform('sum')
        prob = (c / s.values)
        win = prob[y == 1]
        return -np.log(np.clip(win, eps, 1)).mean()
    # 市場単独
    ll_mkt = race_ll(np.exp(lp))
    if not use_blend:
        return ll_mkt, None
    # ブレンド係数を winner対数尤度最大化でfit

    def negll(ab):
        a, b = ab
        z = a * lf + b * lp
        z = z - pd.Series(z).groupby(rid).transform('max').values
        c = np.exp(z)
        d2 = d.assign(_c=c)
        s = d2.groupby('race_id')['_c'].transform('sum').values
        prob = c / s
        return -np.log(np.clip(prob[y == 1], eps, 1)).mean()
    res = minimize(negll, [0.5, 1.0], method='Nelder-Mead')
    ll_blend = res.fun
    return ll_mkt, (ll_blend, res.x)


def run(df, prepare, label, n_folds=5):
    races = df[['today_race_date', 'race_id']].drop_duplicates().sort_values(['today_race_date', 'race_id'])['race_id'].tolist()
    n = len(races); start = n // 2; block = (n - start) // n_folds
    aucs, dlls = [], []
    for k in range(n_folds):
        te_lo = start + k * block; te_hi = start + (k + 1) * block if k < n_folds - 1 else n
        test_ids = set(races[te_lo:te_hi]); train_ids = set(races[:te_lo])
        tr = df['race_id'].isin(train_ids).values; te = df['race_id'].isin(test_ids).values
        if label == 'baseline':
            X, y, _ = prepare(df); cats = 'auto'
        else:
            X, y, info = prepare(df, tr); cats = info[0]
        clf = lgb.LGBMClassifier(objective='binary', n_estimators=500, learning_rate=0.03,
                                 num_leaves=31, max_depth=5, min_child_samples=30, subsample=0.8,
                                 colsample_bytree=0.8, reg_lambda=5.0, random_state=42, n_jobs=-1, verbosity=-1)
        if cats == 'auto':
            clf.fit(X[tr], y[tr])
        else:
            clf.fit(X[tr], y[tr], categorical_feature=cats)
        p = clf.predict_proba(X[te])[:, 1]
        dt = df[te].copy(); dt['p'] = p
        auc = roc_auc_score(y[te], p)
        ll_mkt, blend = winner_ll(dt, 'p', use_blend=True)
        dll = ll_mkt - blend[0]
        aucs.append(auc); dlls.append(dll)
        logger.info(f"[{label}] fold{k+1} AUC={auc:.4f} ΔLL={dll:+.4f} (α,β={blend[1].round(2)})")
    return np.array(aucs), np.array(dlls)


def main():
    df = load_data()
    logger.info(f"{len(df)}行 / {df['race_id'].nunique()}レース")
    ba, bd = run(df, base_prepare, 'baseline')
    ia, idl = run(df, improved_prepare, 'improved')
    print("\n" + "=" * 70)
    print("  前処理改善 効果検証(5fold ウォークフォワード)")
    print("=" * 70)
    print(f"  {'':10}{'AUC平均':>10}{'ΔLL平均':>12}{'ΔLL σ':>10}{'>0 fold':>9}")
    print(f"  {'baseline':10}{ba.mean():>10.4f}{bd.mean():>+12.4f}{bd.std():>10.4f}{int((bd>0).sum()):>6}/5")
    print(f"  {'improved':10}{ia.mean():>10.4f}{idl.mean():>+12.4f}{idl.std():>10.4f}{int((idl>0).sum()):>6}/5")
    print("=" * 70)
    print("  ΔLL>0が安定(σ内で+) → 市場に無い情報を足せた=改善が効いた")
    print("  ΔLL≈0 のまま → 前処理を直しても市場効率の壁。精度でなく情報の問題が確定")


if __name__ == '__main__':
    main()
