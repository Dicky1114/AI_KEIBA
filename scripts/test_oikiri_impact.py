#!/usr/bin/env python3
"""
@file    test_oikiri_impact.py
@brief   調教評価/気配が ΔLL に効くかを「調教カバー済レース限定」で途中検証する
@version 1.0.0  2026-06-28 (Dicky1114)

調教は古い順に取得中なので、調教データのある前半レースだけに絞り、
ウォークフォワードΔLLを「調教あり特徴 vs なし」で比較する。
※サンプルが小さい段階では結論は暫定(ノイズ大)。
"""
import os, sys, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scripts.run_roi_analysis import load_data
from scripts.market_blend import fundamental_features, fit_blend, winner_logloss, softmax_by_race, GROUP_COLS, EPS
from scripts.science_menu import prep
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
N_FOLDS = 4
OIKIRI = ['oikiri_grade', 'oikiri_sentiment']


def wf(df, X, label):
    import lightgbm as lgb
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races); start = int(n*0.4); block = (n-start)//N_FOLDS
    Xv = X.values.astype('float32'); y = df['is_win'].values
    dlls = []
    for k in range(N_FOLDS):
        tr_end = start + k*block; te_end = start+(k+1)*block if k<N_FOLDS-1 else n
        tl = races[:tr_end]; cut=int(len(tl)*0.7)
        A=df['race_id'].isin(set(tl[:cut])).values; B=df['race_id'].isin(set(tl[cut:])).values
        T=df['race_id'].isin(set(races[tr_end:te_end])).values
        m=lgb.LGBMClassifier(objective='binary',n_estimators=400,learning_rate=0.03,num_leaves=31,
            max_depth=5,min_child_samples=30,subsample=0.8,colsample_bytree=0.8,reg_lambda=5.0,
            random_state=42,n_jobs=-1,verbosity=-1)
        m.fit(Xv[A], y[A])
        d=df.copy(); d['f_raw']=m.predict_proba(Xv)[:,1]
        d['f_norm']=softmax_by_race(d.assign(_lf=np.log(np.clip(d['f_raw'],EPS,1))),'_lf')
        a,b=fit_blend(d[B])
        d['z']=a*np.log(np.clip(d['f_norm'],EPS,1))+b*np.log(np.clip(d['pi'],EPS,1))
        d['c']=softmax_by_race(d,'z')
        t=d[T]; dlls.append(winner_logloss(t,'pi')-winner_logloss(t,'c'))
    dlls=np.array(dlls)
    pos=int((dlls>0).sum())
    print(f"  {label:<22} ΔLL平均={dlls.mean():+.4f} σ={dlls.std():.4f} ＋fold={pos}/{N_FOLDS}  [{' '.join(f'{x:+.3f}' for x in dlls)}]")
    return dlls


def main():
    df = prep(load_data())
    cov = df['oikiri_grade'].notna()
    cov_races = df.loc[cov, 'race_id'].unique()
    sub = df[df['race_id'].isin(cov_races)].copy()
    logger.info(f"調教カバー済: {len(cov_races)}レース / {len(sub)}行 (全{df['race_id'].nunique()}レース中)")
    X, feat = fundamental_features(sub)
    print("\n" + "="*84)
    print(f"  調教の効果(途中検証・カバー{len(cov_races)}レース限定・ウォークフォワードΔLL)")
    print("="*84)
    wf(sub, X, "調教あり(全特徴)")
    wf(sub, X.drop(columns=[c for c in OIKIRI if c in X.columns]), "調教なし")
    print("="*84)
    print("  ※ サンプル小=ノイズ大。差が σ 未満なら『まだ判定不能』。")


if __name__ == '__main__':
    main()
