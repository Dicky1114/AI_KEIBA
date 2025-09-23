# 競馬予測システム (KEIBA)

## 概要

競馬予測システムは、機械学習とデータ分析を活用した競馬の予測プラットフォームです。レースデータの収集から予測、結果分析まで一連の機能を提供します。

## 🎨 管理画面カスタマイズ

最新のアップデートで、Django管理画面をモダンなUI/UXデザインにカスタマイズしました：

- **🎯 レスポンシブデザイン**: デスクトップ、タブレット、モバイルに対応
- **🎨 ダークテーマ**: 目に優しいダークカラーパレット
- **📱 ハンバーガーメニュー**: サイドバーの表示/非表示制御
- **⚡ 高速レスポンス**: 最適化されたCSS/JavaScript
- **🔧 コンポーネント分離**: 保守性の高いコード構成

詳細は [管理画面設計書](docs/admin_design_specification.md) をご覧ください。

## 特徴

- 🏁 **包括的なデータ管理**: レース、馬、騎手、競馬場の詳細データ管理
- 🤖 **機械学習予測**: 複数のアルゴリズムによる予測モデル
- 📊 **高度な分析機能**: データ可視化と統計分析
- 🔄 **自動データ収集**: Webスクレイピングによる自動データ更新
- 📱 **REST API**: モバイルアプリや外部サービス連携
- 🔔 **通知システム**: 重要なイベントの通知機能
- 🐳 **Docker対応**: 簡単なデプロイメント環境

## システム構成

```
KEIBA/
├── apps/                    # アプリケーション群
│   ├── core/               # コア機能（共通ベースクラス、ユーティリティ）
│   ├── accounts/           # ユーザー管理・認証
│   ├── races/              # レース管理
│   ├── horses/             # 馬・騎手管理
│   ├── predictions/        # 予測システム
│   ├── scraping/          # データ収集
│   ├── analytics/         # データ分析・可視化
│   └── notifications/     # 通知システム
├── config/                 # Django設定
├── ml_models/             # 機械学習モデル格納
├── tests/                 # テスト
├── docker/               # Docker設定
└── docs/                 # ドキュメント
```

## 技術スタック

### Backend
- **Django 5.1.4** - Webフレームワーク
- **Django REST Framework** - API開発
- **PostgreSQL** - メインデータベース
- **Redis** - キャッシュ・セッション・タスクキュー
- **Celery** - 非同期タスク処理

### Machine Learning
- **scikit-learn** - 機械学習ライブラリ
- **XGBoost** - 勾配ブースティング
- **LightGBM** - 高速勾配ブースティング
- **pandas/numpy** - データ処理

### Data Collection
- **Selenium** - ブラウザ自動化
- **BeautifulSoup4** - HTMLパーシング
- **requests** - HTTP クライアント

### Visualization
- **matplotlib/seaborn** - 静的グラフ
- **plotly** - インタラクティブグラフ

### Infrastructure
- **Docker/Docker Compose** - コンテナ化
- **Nginx** - Webサーバー（本番環境）
- **Gunicorn** - WSGIサーバー

## セットアップ

### 前提条件
- Python 3.13+
- PostgreSQL 15+
- Redis 7+
- Git

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd KEIBA
```

### 2. 仮想環境の作成
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

### 3. 依存関係のインストール
```bash
pip install -r requirements/development.txt
```

### 4. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集して必要な設定を追加
```

### 5. データベースの設定
```bash
# PostgreSQL データベース作成
createdb keiba_db

# マイグレーション
python manage.py makemigrations
python manage.py migrate

# スーパーユーザー作成
python manage.py createsuperuser
```

### 6. 開発サーバー起動
```bash
python manage.py runserver
```

## Docker での起動

### 開発環境
```bash
docker-compose up -d
```

### 本番環境
```bash
docker-compose -f docker-compose.yml --profile production up -d
```

## API エンドポイント

### 認証
- `POST /api/v1/accounts/login/` - ログイン
- `POST /api/v1/accounts/logout/` - ログアウト
- `POST /api/v1/accounts/register/` - ユーザー登録

### レース
- `GET /api/v1/races/` - レース一覧
- `GET /api/v1/races/{id}/` - レース詳細
- `GET /api/v1/races/{id}/entries/` - 出走馬一覧

### 予測
- `GET /api/v1/predictions/` - 予測一覧
- `POST /api/v1/predictions/` - 予測作成
- `GET /api/v1/predictions/{id}/` - 予測詳細

### 分析
- `GET /api/v1/analytics/race-stats/` - レース統計
- `GET /api/v1/analytics/horse-performance/` - 馬の成績分析
- `GET /api/v1/analytics/trends/` - トレンド分析

## 主要機能

### 1. データ収集（Scraping）
- netkeiba.com からの自動データ収集
- レース結果、馬情報、騎手情報の取得
- レート制限とエラーハンドリング

### 2. 予測システム
- 複数の機械学習アルゴリズム
- アンサンブル学習
- 予測精度の評価と改善

### 3. 分析機能
- レース傾向分析
- 馬の能力分析
- 騎手の成績分析
- 競馬場別の特徴分析

### 4. 通知システム
- 重要レースのリマインド
- 予測結果の通知
- システムアラート

## 管理コマンド

### データ収集
```bash
# 指定日のレースデータを収集
python manage.py scrape_race_data --date 2024-01-01

# 馬の過去成績を更新
python manage.py update_horse_performance
```

### 予測
```bash
# 予測モデルを学習
python manage.py train_prediction_model

# 予測を実行
python manage.py run_predictions --date 2024-01-01
```

### データ管理
```bash
# データベースのバックアップ
python manage.py backup_database

# 古いログファイルを削除
python manage.py cleanup_logs --days 30
```

## テスト

### 全テスト実行
```bash
pytest
```

### カバレッジ付きテスト
```bash
pytest --cov=apps --cov-report=html
```

### 特定のアプリのテスト
```bash
pytest tests/test_predictions/
```

## コード品質

### フォーマット
```bash
black .
isort .
```

### リンティング
```bash
flake8
```

### pre-commit フック
```bash
pre-commit install
pre-commit run --all-files
```

## デプロイメント

### ステージング環境
```bash
# 環境変数設定
export DJANGO_SETTINGS_MODULE=config.settings.staging

# 静的ファイル収集
python manage.py collectstatic --noinput

# マイグレーション
python manage.py migrate

# サーバー起動
gunicorn config.wsgi:application
```

### 本番環境
```bash
# Docker Compose での本番デプロイ
docker-compose -f docker-compose.yml --profile production up -d
```

## 監視とログ

### ログファイル
- `logs/django/` - Djangoログ
- `logs/celery/` - Celeryログ
- `logs/scraping/` - スクレイピングログ
- `logs/ml/` - 機械学習ログ

### ヘルスチェック
- `GET /health/` - システム状態確認

## トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   ```bash
   # PostgreSQLサービス確認
   sudo systemctl status postgresql
   
   # 接続設定確認
   python manage.py dbshell
   ```

2. **Celeryタスクが実行されない**
   ```bash
   # Celeryワーカー起動
   celery -A config worker --loglevel=info
   
   # タスク確認
   celery -A config inspect active
   ```

3. **スクレイピングエラー**
   ```bash
   # ChromeDriverの確認
   which chromedriver
   
   # ログ確認
   tail -f logs/scraping/scraping.log
   ```

## 貢献

1. フォークを作成
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## サポート

- Issue: [GitHub Issues](link-to-issues)
- ドキュメント: [docs/](docs/)
- API仕様書: [docs/api/](docs/api/)

---

**注意**: このシステムは教育・研究目的で開発されています。実際の賭博行為は法律で禁止されている場合がありますので、各地域の法律に従ってご利用ください。
# KEIBA
