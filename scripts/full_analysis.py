#!/usr/bin/env python3
"""
@file    full_analysis.py
@brief   完全分析: 目的変数(勝/タイム) × モデル(LGB/Logistic/MLP/アンサンブル) × 特徴量(全/削減)
         を全てウォークフォワードΔLLで採点する。
@version 1.0.0  2026-06-29 (Dicky1114)

各構成: 1段目で「各馬のスコア(高い=勝ち寄り)」→レース内softmax=f_norm
        →市場ブレンド(α,β)→test winner logloss で ΔLL(市場−ブレンド)。
        複数foldで安定>0 のみ「市場に勝てる」候補。
"""
import os, sys, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scripts.run_roi_analysis import load_data
from scripts.market_blend import fundamental_features, fit_blend, winner_logloss, softmax_by_race, GROUP_COLS, EPS
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
N_FOLDS = 5


def prep(df):
    df = df.copy()
    df['rank_int'] = pd.to_numeric(df['rank'], errors='coerce')
    df['is_win'] = (df['rank_int'] == 1).astype(int)
    df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
    df = df[df['odds'] > 0].copy()
    df['inv_odds'] = 1.0 / df['odds']
    df['pi'] = df.groupby('race_id')['inv_odds'].transform(lambda s: s / s.sum())
    df['target_time'] = pd.to_numeric(df.get('target_time'), errors='coerce')
    return df


def score_fn(kind):
    """kind→ fit(Xtr,df_tr)→predict(Xall)= per-row score(高い=勝ち寄り) を返す。"""
    import lightgbm as lgb
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler

    def f(Xtr, dtr, Xall, df_all):
        if kind == 'LGB勝(binary)':
            m = lgb.LGBMClassifier(objective='binary', n_estimators=400, learning_rate=0.03, num_leaves=31,
                max_depth=5, min_child_samples=30, subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
                random_state=42, n_jobs=-1, verbosity=-1)
            m.fit(Xtr, dtr['is_win'].values)
            return m.predict_proba(Xall)[:, 1]
        if kind == 'LGBタイム回帰':
            m = lgb.LGBMRegressor(objective='regression', n_estimators=400, learning_rate=0.03, num_leaves=31,
                max_depth=5, min_child_samples=30, subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
                random_state=42, n_jobs=-1, verbosity=-1)
            mask = dtr['target_time'].notna().values
            m.fit(Xtr[mask], dtr['target_time'].values[mask])
            return -m.predict(Xall)  # 速い(小タイム)=高スコア
        if kind in ('Logistic', 'MLP(DL)', 'アンサンブル'):
            sc = StandardScaler()
            Xtr_s = sc.fit_transform(np.nan_to_num(Xtr, nan=-1))
            Xall_s = sc.transform(np.nan_to_num(Xall, nan=-1))
            y = dtr['is_win'].values
            outs = []
            if kind in ('Logistic', 'アンサンブル'):
                lr = LogisticRegression(max_iter=1000, C=0.5); lr.fit(Xtr_s, y)
                outs.append(lr.predict_proba(Xall_s)[:, 1])
            if kind in ('MLP(DL)', 'アンサンブル'):
                mlp = MLPClassifier(hidden_layer_sizes=(48, 16), alpha=1e-2, max_iter=120,
                                    early_stopping=True, random_state=42)
                mlp.fit(Xtr_s, y); outs.append(mlp.predict_proba(Xall_s)[:, 1])
            if kind == 'アンサンブル':
                m = lgb.LGBMClassifier(objective='binary', n_estimators=400, learning_rate=0.03, num_leaves=31,
                    max_depth=5, min_child_samples=30, reg_lambda=5.0, random_state=42, n_jobs=-1, verbosity=-1)
                m.fit(Xtr, y); outs.append(m.predict_proba(Xall)[:, 1])
            return np.mean(outs, axis=0)
        raise ValueError(kind)
    return f


def walkforward(df, X, kind):
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races); start = int(n * 0.4); block = (n - start) // N_FOLDS
    Xv = X.values.astype('float32')
    fn = score_fn(kind)
    dlls = []
    for k in range(N_FOLDS):
        tr_end = start + k * block; te_end = start + (k + 1) * block if k < N_FOLDS - 1 else n
        tl = races[:tr_end]; cut = int(len(tl) * 0.7)
        A = df['race_id'].isin(set(tl[:cut])).values
        B = df['race_id'].isin(set(tl[cut:])).values
        T = df['race_id'].isin(set(races[tr_end:te_end])).values
        score = fn(Xv[A], df[A], Xv, df)
        d = df.copy(); d['score'] = score
        d['f_norm'] = softmax_by_race(d, 'score')
        a, b = fit_blend(d[B])
        d['z'] = a * np.log(np.clip(d['f_norm'], EPS, 1)) + b * np.log(np.clip(d['pi'], EPS, 1))
        d['c'] = softmax_by_race(d, 'z')
        t = d[T]; dlls.append(winner_logloss(t, 'pi') - winner_logloss(t, 'c'))
    return np.array(dlls)


def main():
    import lightgbm as lgb
    df = prep(load_data())
    X, feat = fundamental_features(df)
    logger.info(f"{df['race_id'].nunique()}レース 特徴量{len(feat)}")
    # 重要度で特徴量削減セットを作る
    m = lgb.LGBMClassifier(objective='binary', n_estimators=300, num_leaves=31, max_depth=5,
        reg_lambda=5.0, random_state=42, n_jobs=-1, verbosity=-1)
    m.fit(X.values, df['is_win'].values)
    imp = pd.Series(m.booster_.feature_importance(importance_type='gain'), index=feat).sort_values(ascending=False)
    top15 = imp.head(15).index.tolist(); top8 = imp.head(8).index.tolist()

    def rep(name, dlls):
        pos = int((dlls > 0).sum())
        mark = '✅' if (pos >= N_FOLDS - 1 and dlls.mean() > 0) else ('△' if pos >= 3 else '❌')
        print(f"  {name:<34}ΔLL平均={dlls.mean():+.4f} σ={dlls.std():.4f} ＋fold={pos}/{N_FOLDS} {mark}")

    print("\n" + "=" * 84)
    print("  完全分析: 目的変数×モデル×特徴量 (ウォークフォワードΔLL / +=市場に勝てる)")
    print("=" * 84)
    print("  [A] モデル比較 (全50特徴)")
    for kind in ['LGB勝(binary)', 'LGBタイム回帰', 'Logistic', 'MLP(DL)', 'アンサンブル']:
        rep(kind, walkforward(df, X, kind))
    print("  [B] 特徴量削減 (LGB勝)")
    rep('全50特徴', walkforward(df, X, 'LGB勝(binary)'))
    rep(f'top15特徴', walkforward(df, X[top15], 'LGB勝(binary)'))
    rep(f'top8特徴', walkforward(df, X[top8], 'LGB勝(binary)'))
    print("=" * 84)
    print(f"  重要度top8: {top8}")
    print("  ※ ✅=安定して市場超え / ❌=増分情報なし")


if __name__ == '__main__':
    main()
