# 競馬予測 分析トラッキング

## 概要

競馬予測MLパイプラインの実験結果・PDCA記録。
各実験の `analysis_YYYYMMDD_HHMMSS.md` が `media/ml_output/` に自動生成される。

---

## パイプライン構成

```
データ取得 (scrape_5years.py)
    ↓
前処理 (ml_training.py → prepare_data)
    ↓
相関特徴量除去 (threshold=0.95)
    ↓
前方特徴量選択 (Forward Feature Selection)
    ↓
GroupTimeSeriesSplit (5-fold, 時系列考慮)
    ↓
LightGBM LambdaRank 学習
    ↓
Optuna ハイパーパラメータ最適化 (オプション)
    ↓
馬単 (Exacta) 上位3頭全通り予測
    ↓
analysis.md 自動生成
```

## モデル構成

| モデル | アルゴリズム | 目的 |
|--------|------------|------|
| LightGBM LambdaRank | ランキング学習 | 着順予測 (メイン) |
| XGBoost Ranker | ランキング学習 | アンサンブル候補 |
| Ridge Regression | 線形回帰 | スタッキングメタモデル |

## 評価指標

| 指標 | 説明 | 目標値 |
|------|------|--------|
| NDCG@3 | 上位3着の順位精度 | > 0.75 |
| 過学習比率 | テスト/検証比 | > 0.85 |
| 馬単的中率 | 上位3頭の2連単的中 | > 15% |
| 回収率 | (払戻 / 掛金) * 100 | > 100% |

## 特徴量カテゴリ

| カテゴリ | 特徴量例 | 備考 |
|---------|---------|------|
| 当日レース | 馬番, 枠番, 性別, 年齢, 斤量, 体重 | 基本情報 |
| 当日オッズ | オッズ, 人気 | 市場評価 |
| レースクラス | G1〜新馬フラグ | ワンホット |
| 過去馬成績 (H1-H3) | 着順, タイム, 上がり, ペース | 直近3走 |
| 過去騎手成績 (J1-J3) | 着順, タイム | 直近3走 |
| 開催条件 | 距離, 馬場, 天気, 頭数, 開催地 | 環境要因 |

## 馬券戦略: 馬単 (Exacta) 上位3頭

```
予測上位3頭 → 3P2 = 6通りの馬単
    1着予測 - 2着予測
    1着予測 - 3着予測
    2着予測 - 1着予測
    2着予測 - 3着予測
    3着予測 - 1着予測
    3着予測 - 2着予測

掛金: 各100円 × 6通り = 600円/レース
期待回収: オッズ依存
```

## 実行コマンド

```bash
# 5年分スクレイピング
python scripts/scrape_5years.py --start 2021-01-01 --end 2026-03-30

# ML学習（基本）
python scripts/run_training.py

# Optuna最適化付き
python scripts/run_training.py --optimize

# 特徴量選択のみ
python scripts/run_training.py --feature-select-only
```

## PDCA サイクル記録

### 2026-03-30 初回構築

- **Plan**: 5年分データで LightGBM LambdaRank + GroupTimeSeriesCV
- **Do**: パイプライン構築完了
- **Check**: (実データ投入後に記録)
- **Act**: (結果に基づき改善)

---

*自動生成される `analysis_*.md` はこのドキュメントの補足詳細として機能する。*
