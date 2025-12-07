# AI_KEIBA - 競馬予測アプリケーション

Django製の競馬予測アプリケーション。Supabase PostgreSQLデータベースとRender.comでホスティング。

## 機能

- 競馬データのスクレイピング
- データ分析とレース予測
- 管理画面でのデータ管理
- Celeryによるバックグラウンドタスク処理

## 技術スタック

- **Backend**: Django 5.1.4
- **Database**: PostgreSQL (Supabase)
- **Cache/Queue**: Redis
- **Task Queue**: Celery
- **Deployment**: Render.com
- **Web Scraping**: Selenium, BeautifulSoup

## ローカル開発環境のセットアップ

### 必要要件

- Python 3.11+
- PostgreSQL
- Redis

### インストール手順

1. リポジトリをクローン
```bash
git clone https://github.com/Dicky1114/AI_KEIBA.git
cd AI_KEIBA
```

2. 仮想環境を作成して有効化
```bash
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
```

3. 依存関係をインストール
```bash
pip install -r requirements.txt
```

4. 環境変数を設定（.envファイルを作成）
```
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=d_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

5. データベースマイグレーション
```bash
python manage.py migrate
```

6. スーパーユーザーを作成
```bash
python manage.py createsuperuser
```

7. 開発サーバーを起動
```bash
python manage.py runserver
```

## Render.comへのデプロイ

このプロジェクトは`render.yaml`を使用して自動的にデプロイされます。

1. Render.comでアカウントを作成
2. GitHubリポジトリを接続
3. 環境変数を設定
4. デプロイを実行

### 必要な環境変数

- `SECRET_KEY`: Djangoのシークレットキー
- `DATABASE_URL`: PostgreSQLデータベースURL（SupabaseまたはRender PostgreSQL）
- `REDIS_URL`: Redis接続URL
- `DJANGO_SETTINGS_MODULE`: `app_config.settings.production`

## プロジェクト構造

```
AI_KEIBA/
├── app_config/          # Django設定
│   ├── settings/
│   │   ├── base.py      # 基本設定
│   │   ├── develop.py   # 開発環境設定
│   │   └── production.py # 本番環境設定
│   ├── urls.py
│   └── wsgi.py
├── app_folder/          # メインアプリケーション
│   ├── models.py
│   ├── views/
│   ├── services/        # スクレイピング・データ処理
│   └── migrations/
├── accounts/            # ユーザー認証
├── templates/           # HTMLテンプレート
├── static/              # 静的ファイル
├── build.sh             # Renderビルドスクリプト
├── render.yaml          # Render設定
└── requirements.txt     # Python依存関係
```

## ライセンス

このプロジェクトは個人使用のためのものです。

## 作者

Dicky1114
