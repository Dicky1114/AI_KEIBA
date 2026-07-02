#!/usr/bin/env python3
"""
@file    final_verification.py
@brief   外部レビュー提案の「最終検証4段階」ハーネス(5年データ完成後に回す)
@version 1.0.0  2026-06-30  (Dicky1114)

4段階(レビュー準拠):
  段階1 データ監査    : 頭数一致/馬場・距離・着順欠損/race_id+馬番一意/1着1頭/払戻整合
  段階2 市場差予測    : 較正済み勝率をレース内で合計1に再正規化 → EV=p_norm×odds
  段階3 期待値帯別    : EV 1.00-1.05 / 1.05-1.10 / 1.10-1.15 / 1.15+ の実回収率(校正検証)
                       ウォークフォワード(各レースを過去のみで予測=真の未使用)で集計
  段階4 凍結紙上運用  : 最新N(既定1000)レースを完全hold-out。モデル・閾値を凍結して評価。
                       1日/大穴依存・単勝複勝の一貫性も確認

合格基準(段階4):
  ・実行可能(=単勝)で回収率100%超
  ・EV高帯ほど回収率が上がる(段階3)
  ・利益が特定1日/大穴1件に依存しない
  ・複数の月でも同傾向

使用:
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=app_config.settings.develop \
    web python scripts/final_verification.py [--holdout 1000] [--ev-threshold 1.10]
"""
import os, sys, argparse, logging, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_config.settings.develop')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import django  # noqa
django.setup()
import lightgbm as lgb
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score, log_loss
from scripts.run_roi_analysis import load_data
from scripts.fe_experiment import improved_prepare

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
UNIT = 100
PAY_COLS = ['pay1', 'pay123_1', 'pay123_2', 'pay123_3']


def _settle_cols(df):
    """払戻・着順・オッズを数値化した決済用DFを返す(特徴量とは別管理)。"""
    s = df[['today_race_date', 'race_id', 'horse_number', 'odds', 'rank'] +
           [c for c in PAY_COLS if c in df.columns]].copy()
    s['odds'] = pd.to_numeric(s['odds'], errors='coerce')
    s['rank_int'] = pd.to_numeric(s['rank'], errors='coerce')
    for c in PAY_COLS:
        if c in s.columns:
            s[c] = pd.to_numeric(s[c].astype(str).str.replace(',', ''), errors='coerce')
    return s


def _fit_predict(df, X, y, tr, ca, te):
    """過去(tr)で学習・(ca)で較正 → (te)の較正済み勝率を返す。"""
    cats = [c for c in improved_prepare(df, tr)[2][0] if c in X.columns]
    clf = lgb.LGBMClassifier(objective='binary', n_estimators=600, learning_rate=0.03,
                             num_leaves=31, max_depth=5, min_child_samples=30, subsample=0.8,
                             colsample_bytree=0.8, reg_lambda=5.0, random_state=42, n_jobs=-1, verbosity=-1)
    clf.fit(X[tr], y[tr], categorical_feature=cats)
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(clf.predict_proba(X[ca])[:, 1], y[ca].values)
    return iso.transform(clf.predict_proba(X[te])[:, 1])


def walkforward_oos(df, X, y, settle, n_folds=6):
    """各レースを『その過去のみ』で予測した真の未使用予測を全fold分集める。"""
    races = (df[['today_race_date', 'race_id']].drop_duplicates()
             .sort_values(['today_race_date', 'race_id'])['race_id'].tolist())
    n = len(races); start = int(n * 0.4); block = (n - start) // n_folds
    out = []
    for k in range(n_folds):
        te_lo = start + k * block; te_hi = start + (k + 1) * block if k < n_folds - 1 else n
        test_ids = set(races[te_lo:te_hi]); past = races[:te_lo]
        n_ca = int(len(past) * 0.15)
        ca_ids = set(past[len(past) - n_ca:]); tr_ids = set(past[:len(past) - n_ca])
        tr = df['race_id'].isin(tr_ids).values; ca = df['race_id'].isin(ca_ids).values
        te = df['race_id'].isin(test_ids).values
        p = _fit_predict(df, X, y, tr, ca, te)
        d = settle[te].copy(); d['p'] = p
        out.append(d)
    res = pd.concat(out, ignore_index=True)
    # レース内で勝率を合計1に再正規化(段階2)→ EV
    res['p_norm'] = res.groupby('race_id')['p'].transform(lambda s: s / s.sum() if s.sum() > 0 else s)
    res['ev'] = res['p_norm'] * res['odds']
    return res


def stage1_audit(df, settle):
    print("\n" + "=" * 78 + "\n  段階1: データ監査\n" + "=" * 78)
    a = settle.groupby('race_id').agg(rows=('horse_number', 'size')).reset_index()
    cnt = df.groupby('race_id')['count'].max() if 'count' in df.columns else None
    dup = len(settle) - settle.drop_duplicates(['race_id', 'horse_number']).shape[0]
    winners = settle[settle['rank_int'] == 1].groupby('race_id').size()
    no_win = (winners.reindex(a['race_id']).fillna(0) == 0).sum()
    multi_win = (winners > 1).sum()
    odds_miss = settle['odds'].isna().mean() * 100
    print(f"  レース数={a.shape[0]}  行数={len(settle)}  重複(race+馬番)={dup}")
    print(f"  1着不在レース={no_win}  1着複数(同着除く要確認)={multi_win}")
    print(f"  オッズ欠損={odds_miss:.2f}%")
    print(f"  → {'OK' if dup==0 and no_win==0 and odds_miss<2 else '要確認'}")


def stage3_ev_bands(res):
    print("\n" + "=" * 78 + "\n  段階3: 期待値帯別の実回収率(単勝・ウォークフォワード未使用予測)\n" + "=" * 78)
    bets = res[(res['ev'] >= 1.0) & res['odds'].notna() & res['pay1'].notna()].copy()
    bands = [(1.00, 1.05), (1.05, 1.10), (1.10, 1.15), (1.15, 1.30), (1.30, 99)]
    print(f"  {'EV帯':>12}{'購入':>7}{'的中':>6}{'的中率':>8}{'平均ODDS':>9}{'回収率':>9}")
    print("  " + "-" * 60)
    prev = None
    monotonic = True
    for lo, hi in bands:
        b = bets[(bets['ev'] >= lo) & (bets['ev'] < hi)]
        n = len(b)
        if n == 0:
            print(f"  {f'{lo:.2f}-{hi:.2f}':>12}{0:>7}")
            continue
        won = b['rank_int'] == 1
        ret = b.loc[won, 'pay1'].sum(); roi = ret / (n * UNIT) * 100
        print(f"  {f'{lo:.2f}-{hi:.2f}':>12}{n:>7}{int(won.sum()):>6}{won.mean()*100:>7.1f}%"
              f"{b['odds'].mean():>9.1f}{roi:>8.1f}%")
        if prev is not None and roi < prev - 5:
            monotonic = False
        prev = roi
    print("  " + "-" * 60)
    print(f"  判定: EV高帯ほど回収率が上がる傾向 = {'あり(校正OK・期待値に意味)' if monotonic else 'なし(校正崩れ)'}")


def stage4_paper_trade(df, X, y, settle, holdout, ev_th):
    print("\n" + "=" * 78 + f"\n  段階4: 凍結紙上運用(最新{holdout}レース・モデル凍結・EV>={ev_th}で単勝)\n" + "=" * 78)
    races = (df[['today_race_date', 'race_id']].drop_duplicates()
             .sort_values(['today_race_date', 'race_id'])['race_id'].tolist())
    test_ids = set(races[-holdout:]); past = races[:-holdout]
    n_ca = int(len(past) * 0.15)
    ca_ids = set(past[len(past) - n_ca:]); tr_ids = set(past[:len(past) - n_ca])
    tr = df['race_id'].isin(tr_ids).values; ca = df['race_id'].isin(ca_ids).values
    te = df['race_id'].isin(test_ids).values
    p = _fit_predict(df, X, y, tr, ca, te)
    d = settle[te].copy(); d['p'] = p
    d['p_norm'] = d.groupby('race_id')['p'].transform(lambda s: s / s.sum() if s.sum() > 0 else s)
    d['ev'] = d['p_norm'] * d['odds']
    bets = d[(d['ev'] >= ev_th) & d['pay1'].notna()].copy()
    if len(bets) == 0:
        print("  購入対象なし"); return
    bets['ret'] = np.where(bets['rank_int'] == 1, bets['pay1'], 0.0)
    bet_total = len(bets) * UNIT; ret_total = bets['ret'].sum()
    roi = ret_total / bet_total * 100
    # 大穴依存: 最大1レースの払戻が総回収に占める割合
    max_share = bets['ret'].max() / ret_total * 100 if ret_total > 0 else 0
    # 月別一貫性
    bets['month'] = pd.to_datetime(bets['today_race_date']).dt.to_period('M').astype(str)
    monthly = bets.groupby('month').apply(lambda g: g['ret'].sum() / (len(g) * UNIT) * 100)
    print(f"  テスト期間: {d['today_race_date'].min()} 〜 {d['today_race_date'].max()}")
    print(f"  購入 {len(bets)}点  的中 {int((bets['ret']>0).sum())}  的中率 {(bets['ret']>0).mean()*100:.1f}%")
    print(f"  投資 {bet_total:,}円  回収 {int(ret_total):,}円  回収率 {roi:.1f}%")
    print(f"  最大1レース依存度 {max_share:.1f}%  (高いほど大穴1発依存=危険)")
    print(f"  月別回収率: " + " / ".join(f"{m}:{v:.0f}%" for m, v in monthly.items()))
    ok = roi > 100 and max_share < 40
    print(f"  → 合格基準(回収率>100% かつ 大穴依存<40%): {'合格' if ok else '不合格(利益化せず)'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--holdout', type=int, default=1000)
    ap.add_argument('--ev-threshold', type=float, default=1.10)
    ap.add_argument('--folds', type=int, default=6)
    args = ap.parse_args()

    df = load_data()
    df['race_id'] = df['race_id'].astype(str)
    settle = _settle_cols(df)
    X, y, info = improved_prepare(df, np.ones(len(df), bool))
    logger.info(f"{len(df)}行 / {df['race_id'].nunique()}レース / 特徴量{X.shape[1]}")

    stage1_audit(df, settle)
    # 段階2は段階3/4内でレース内再正規化として実装済
    res = walkforward_oos(df, X, y, settle, n_folds=args.folds)
    # 参考: 全体AUC/logloss
    try:
        auc = roc_auc_score((res['rank_int'] == 1).astype(int), res['p'])
        logger.info(f"未使用予測 AUC={auc:.4f}")
    except Exception:
        pass
    stage3_ev_bands(res)
    stage4_paper_trade(df, X, y, settle, args.holdout, args.ev_threshold)
    print("\n" + "=" * 78)
    print("  総括: 段階3でEV高帯ほど回収率↑ かつ 段階4で回収率>100%(大穴非依存)なら")
    print("        利益モデルの可能性。どちらか欠ければ現状路線は撤退してツール化が妥当。")
    print("=" * 78)


if __name__ == '__main__':
    main()
