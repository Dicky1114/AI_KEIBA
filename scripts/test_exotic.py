#!/usr/bin/env python3
"""
@file    test_exotic.py
@brief   Codex#3: 券種別(馬連/3連複/3連単)を Harville+Benter補正で勝率から導出し ΔLL 直接判定
@version 1.0.0  2026-06-29 (Dicky1114)

勝率 c(市場ブレンド済) から各券種の確率を導出(Benter γ=0.81, δ=0.65補正):
  σ_i = softmax(γ·log c_i), τ_i = softmax(δ·log c_i)
  3連単 P(i,j,k順) = c_i · σ_j/(1-σ_i) · τ_k/(1-τ_i-τ_j)
  馬連  P({i,j})  = c_i·σ_j/(1-σ_i) + c_j·σ_i/(1-σ_j)
  3連複 P({i,j,k}) = Σ全6順列の3連単P
市場の含意確率 = (1-控除率)/(払戻/100)。
ΔLL = 市場含意の-logloss − モデルの-logloss(各券種・的中組のみ)。>0=市場超え。
"""
import os, sys, logging, warnings
from itertools import permutations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scripts.run_roi_analysis import load_data
from scripts.market_blend import fundamental_features, fit_blend, softmax_by_race, GROUP_COLS, EPS
from scripts.science_menu import prep
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
N_FOLDS = 5
GAMMA, DELTA = 0.81, 0.65
TAKEOUT = {'馬連': 0.225, '3連複': 0.25, '3連単': 0.275}


def predict_c(df, X, A, B):
    import lightgbm as lgb
    m = lgb.LGBMClassifier(objective='binary', n_estimators=400, learning_rate=0.03, num_leaves=31,
        max_depth=5, min_child_samples=30, subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
        random_state=42, n_jobs=-1, verbosity=-1)
    m.fit(X.values[A], df['is_win'].values[A])
    d = df.copy(); d['f_raw'] = m.predict_proba(X.values)[:, 1]
    d['f_norm'] = softmax_by_race(d.assign(_lf=np.log(np.clip(d['f_raw'], EPS, 1))), '_lf')
    a, b = fit_blend(d[B])
    d['z'] = a*np.log(np.clip(d['f_norm'], EPS, 1)) + b*np.log(np.clip(d['pi'], EPS, 1))
    d['c'] = softmax_by_race(d, 'z')
    return d


def _norm(p):
    p = np.clip(np.asarray(p, float), EPS, None)
    return p / p.sum()


def exotic_probs(c, hn, a1, a2, a3):
    """的中組のモデル確率を返す(馬連/3連複/3連単)。c=勝率, hn=馬番list。"""
    idx = {h: i for i, h in enumerate(hn)}
    if a1 not in idx or a2 not in idx or a3 not in idx:
        return None
    c = _norm(c)
    sg = _norm(c ** GAMMA)   # σ
    tn = _norm(c ** DELTA)   # τ
    i, j, k = idx[a1], idx[a2], idx[a3]

    def trifecta(x, y, z):
        d1 = 1 - sg[x]
        d2 = 1 - tn[x] - tn[y]
        if d1 <= EPS or d2 <= EPS:
            return EPS
        return c[x] * (sg[y] / d1) * (tn[z] / d2)
    # 馬連(順不同 i,j)
    umaren = c[i]*sg[j]/max(1-sg[i], EPS) + c[j]*sg[i]/max(1-sg[j], EPS)
    # 3連単(順序 i,j,k)
    santan = trifecta(i, j, k)
    # 3連複(順不同{i,j,k}=6順列の和)
    sanfuku = sum(trifecta(*perm) for perm in permutations([i, j, k]))
    return {'馬連': umaren, '3連複': sanfuku, '3連単': santan}


def main():
    df = prep(load_data())
    X, feat = fundamental_features(df)
    races = df[GROUP_COLS].drop_duplicates().sort_values(GROUP_COLS)['race_id'].tolist()
    n = len(races); start = int(n*0.4); block = (n-start)//N_FOLDS
    paycol = {'馬連': 'pay12_21', '3連複': 'pay123_321', '3連単': 'pay123_123'}

    fold = {b: [] for b in TAKEOUT}     # bet -> list(fold ΔLL)
    for kf in range(N_FOLDS):
        tr_end = start+kf*block; te_end = start+(kf+1)*block if kf < N_FOLDS-1 else n
        tl = races[:tr_end]; cut = int(len(tl)*0.7)
        A = df['race_id'].isin(set(tl[:cut])).values
        B = df['race_id'].isin(set(tl[cut:])).values
        T = set(races[tr_end:te_end])
        d = predict_c(df, X, A, B)
        t = d[d['race_id'].isin(T)]
        acc = {b: {'m': [], 'k': []} for b in TAKEOUT}  # model/market -log
        for rid, g in t.groupby('race_id'):
            g = g.copy(); g['rank_int'] = pd.to_numeric(g['rank'], errors='coerce')
            w = [g[g['rank_int'] == r]['horse_number'] for r in (1, 2, 3)]
            if any(len(x) == 0 for x in w):
                continue
            a1, a2, a3 = (str(x.iloc[0]) for x in w)
            hn = [str(x) for x in g['horse_number']]
            ep = exotic_probs(g['c'].to_numpy(), hn, a1, a2, a3)
            if ep is None:
                continue
            for b in TAKEOUT:
                pv = pd.to_numeric(g[paycol[b]], errors='coerce').dropna()
                if len(pv) == 0 or pv.iloc[0] <= 0:
                    continue
                mk = (1-TAKEOUT[b]) / (float(pv.iloc[0])/100.0)   # 市場含意確率
                acc[b]['m'].append(-np.log(max(ep[b], EPS)))
                acc[b]['k'].append(-np.log(max(min(mk, 1.0), EPS)))
        for b in TAKEOUT:
            if acc[b]['m']:
                dll = np.mean(acc[b]['k']) - np.mean(acc[b]['m'])  # 市場 - モデル
                fold[b].append(dll)

    print("\n" + "="*78)
    print("  Codex#3: 券種別 ΔLL (Harville+Benter補正・市場含意 vs モデル / +=市場超え)")
    print("="*78)
    print(f"  {'券種':>6}{'ΔLL平均':>10}{'σ':>8}{'＋fold':>8}  fold別")
    print("-"*78)
    for b in TAKEOUT:
        arr = np.array(fold[b])
        pos = int((arr > 0).sum())
        mark = '✅' if pos >= N_FOLDS-1 and arr.mean() > 0 else ('△' if pos >= 3 else '❌')
        print(f"  {b:>6}{arr.mean():>+10.4f}{arr.std():>8.4f}{pos:>5}/{len(arr)}  [{' '.join(f'{x:+.3f}' for x in arr)}] {mark}")
    print("="*78)
    print("  ※ 各券種で安定>0なら市場超え。負なら券種別に定式化しても勝てない")


if __name__ == '__main__':
    main()
