# 03_keiba — 競馬データ解析プラットフォーム

> プロジェクトコンテキスト。セッション開始時に必ず一読。  
> **最終更新**: 2026-07-01 | **責任者**: dickey

---

## プロジェクト概要

- **目的**: 競馬レース・馬・騎手データの収集・解析・予測
- **技術スタック**: Django 5.1 + PostgreSQL + Celery/Redis + Tailwind
- **ステータス**: 活発開発中（スクレイピング v2 並列化・ML精度改善進行中）

---

## ディレクトリ構造（主要部分）

```
app_config/          ← Django設定（settings/base.py, develop.py）
app_folder/          ← 旧フォルダ構造（段階的に apps/ へ移行中）
  /migrations/       ← DB マイグレーション
  /services/         ← ビジネスロジック（get_*.py, insert_db.py）
  /utils/            ← ユーティリティ（driver.py など）
apps/                ← 新 Django app 構造（accounts, core, horses, races, scraping等）
  /core/             ← 中核ロジック・共通ビュー
  /horses/           ← 馬マスタ・系統図
  /races/            ← レース・結果データ
  /scraping/         ← Web スクレイピング（JRA等）
  /predictions/      ← ML予測モデル
scripts/             ← スクレイピング・バッチスクリプト（5年分取得、分析等）
docs/                ← アーキテクチャ・設計書（アウトデート中）
```

---

## 開発フロー（セッション別）

### Backend セッション (Django/Python)
- **ポート**: 8303 (Django runserver) / Redis: localhost:6379
- **起動**: `dev-start keiba` → Django dev server + Celery worker
- **DB**: keiba_db (PostgreSQL) — 環境変数で localhost or docker-compose db に対応
- **マイグレーション**: `python manage.py migrate`

### Frontend セッション (Tailwind/Templates)
- **ファイル**: `config/templates/` (Django テンプレート)
- **スタイル**: Tailwind CSS (tailwind.config.js 等で定義)
- **ホットリロード**: Django dev server が自動リロード

---

## 重要な環境変数

| 変数 | 説明 | 必須 | 本番設定 |
|------|------|------|---------|
| `DJANGO_SECRET_KEY` | Django シークレットキー | ✅ | `openssl rand -hex 32` で生成 |
| `DB_HOST` | PostgreSQL ホスト | ✅ | RDS エンドポイント or Render DB |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | DB 認証 | ✅ | 環境変数 or SecretsManager |
| `REDIS_URL` | Redis 接続先 | ✅ | ElastiCache or Render Redis |
| `DEBUG` | デバッグモード | ✅ | 本番は `False` |
| `ENVIRONMENT` | 環境識別 | ✅ | `development` / `staging` / `production` |

---

## 既知の欠落・課題（優先順）

| 課題 | 優先度 | 着手者 | 期限 |
|------|--------|--------|------|
| **CI/CD 未設定** | 🔴 Critical | — | TBD |
| **設計書がアウトデート** (docs/architecture.md 280日未更新) | 🟠 High | — | TBD |
| **スクレイピング v2 並列化の精度検証** | 🟠 High | — | TBD |
| 本番秘密鍵管理（AWS SecretsManager 未統合） | 🟠 High | — | TBD |
| E2E テスト未設定 | 🟡 Medium | — | TBD |

---

## セキュリティチェックリスト（重要）

- [x] .gitignore に `.env` 保護
- [ ] **CI/CD でシークレット スキャン (gitleaks) 有効化** (TODO)
- [ ] **本番 SECRET_KEY は環境変数化** (2026-07-01 実装)
- [ ] .env.example テンプレート作成 (2026-07-01 実装)
- [ ] Render/AWS SecretsManager 連携 (TODO)
- [ ] HTTPS/HSTS 設定確認 (TODO)

---

## 使うべきスキル・エージェント

| スキル | 用途 | 起動コマンド |
|--------|------|-----------|
| 70-g-security | セキュリティレビュー・脆弱性チェック | `/70-security` |
| 81-g-infra | CI/CD・Docker・デプロイ | `/81-infra` |
| 60-g-test | テスト・TDD | `/60-test` |
| 61-g-review | コードレビュー (7軸) | `/61-review` |
| 40-g-db-query | PostgreSQL クエリ・パフォーマンス | `/40-db-query` |
| 51-g-rag | LLMパイプライン（予測モデル用） | `/51-rag` |

---

## 参考資料・リンク

- **Django 公式**: https://docs.djangoproject.com/en/5.1/
- **Celery**: https://docs.celeryproject.io/ (Redis broker)
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Render**: https://render.com/docs (本番デプロイ先)

---

## セッション外注

- 関連セッション: 02_platform (API設計・LLM統合)
- 参考プロジェクト: 01_digitive/* (Django 他プロジェクト)
