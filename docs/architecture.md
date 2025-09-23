# システムアーキテクチャ

## 全体構成

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │     API         │    │   Background    │
│                 │    │                 │    │     Tasks       │
│ ・Web UI        │◄──►│ ・Django REST   │◄──►│ ・Celery        │
│ ・Mobile App    │    │   Framework     │    │ ・Scraping      │
│ ・Dashboard     │    │ ・Authentication│    │ ・ML Training   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │     Cache       │    │   File Storage  │
│                 │    │                 │    │                 │
│ ・PostgreSQL    │    │ ・Redis         │    │ ・Media Files   │
│ ・Race Data     │    │ ・Sessions      │    │ ・ML Models     │
│ ・User Data     │    │ ・Task Queue    │    │ ・Logs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## アプリケーション構成

### Core (apps.core)
**役割**: 共通機能とベースクラス
- 抽象ベースモデル（TimeStampedModel）
- 共通Mixin（認証、権限、API応答）
- バリデーター
- ユーティリティ関数

### Accounts (apps.accounts)
**役割**: ユーザー管理と認証
- カスタムユーザーモデル
- 認証・認可
- プロフィール管理
- 権限制御

### Races (apps.races)
**役割**: レース関連データ管理
- レースモデル（Race, Venue, Entry, Result）
- レースデータの CRUD 操作
- 検索・フィルタリング
- API エンドポイント

### Horses (apps.horses)
**役割**: 馬・騎手データ管理
- 馬モデル（Horse, Jockey, Performance）
- 血統管理
- 成績履歴
- パフォーマンス統計

### Predictions (apps.predictions)
**役割**: 予測システム
- 予測モデル管理
- アルゴリズム実装
- 予測実行
- 精度評価

### Scraping (apps.scraping)
**役割**: データ収集
- Webスクレイピング
- データソース管理
- レート制限
- エラーハンドリング

### Analytics (apps.analytics)
**役割**: データ分析・可視化
- 統計分析
- データ可視化
- レポート生成
- トレンド分析

### Notifications (apps.notifications)
**役割**: 通知システム
- 通知設定
- 配信チャンネル（メール、プッシュ）
- スケジュール通知
- 通知履歴

## データベース設計

### ERD概要
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │     │    Race     │     │    Horse    │
│             │     │             │     │             │
│ ・id        │     │ ・id        │     │ ・id        │
│ ・username  │     │ ・name      │     │ ・name      │
│ ・email     │     │ ・date      │     │ ・birth_date│
│ ・is_staff  │     │ ・venue     │     │ ・sex       │
└─────────────┘     └─────────────┘     └─────────────┘
        │                   │                   │
        │                   ▼                   │
        │           ┌─────────────┐              │
        │           │ RaceEntry   │              │
        │           │             │              │
        │           │ ・race_id   │◄─────────────┘
        │           │ ・horse_id  │
        │           │ ・jockey_id │
        │           │ ・odds      │
        │           └─────────────┘
        │                   │
        ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ Prediction  │     │ RaceResult  │
│             │     │             │
│ ・race_id   │     │ ・entry_id  │
│ ・model     │     │ ・position  │
│ ・confidence│     │ ・time      │
│ ・created_by│     │ ・payout    │
└─────────────┘     └─────────────┘
```

### 主要テーブル関係

1. **User ←→ Prediction**: 1対多（ユーザーは複数の予測を作成）
2. **Race ←→ RaceEntry**: 1対多（レースには複数の出走馬）
3. **Horse ←→ RaceEntry**: 1対多（馬は複数のレースに出走）
4. **RaceEntry ←→ RaceResult**: 1対1（出走馬には1つの結果）
5. **Horse ←→ Horse**: 多対多（血統関係）

## API設計

### RESTful エンドポイント

```
/api/v1/
├── accounts/
│   ├── login/                 POST
│   ├── logout/                POST
│   ├── register/              POST
│   └── profile/               GET, PUT
├── races/
│   ├── /                      GET, POST
│   ├── {id}/                  GET, PUT, DELETE
│   ├── {id}/entries/          GET
│   └── {id}/results/          GET
├── horses/
│   ├── /                      GET, POST
│   ├── {id}/                  GET, PUT, DELETE
│   └── {id}/performances/     GET
├── predictions/
│   ├── /                      GET, POST
│   ├── {id}/                  GET, PUT, DELETE
│   └── evaluate/              POST
├── analytics/
│   ├── race-stats/            GET
│   ├── horse-performance/     GET
│   ├── trends/                GET
│   └── reports/               GET, POST
└── scraping/
    ├── jobs/                  GET, POST
    └── jobs/{id}/             GET, PUT
```

### 認証・認可

```python
# JWT トークンベース認証
Authorization: Bearer <token>

# 権限レベル
- Anonymous: 基本データ閲覧のみ
- User: 予測作成・閲覧
- Premium: 高度分析機能
- Staff: データ管理
- Admin: システム管理
```

## セキュリティ

### 実装済み対策

1. **認証・認可**
   - JWT トークン認証
   - 権限ベースアクセス制御
   - CSRF 保護

2. **データ保護**
   - SQL インジェクション対策（ORM使用）
   - XSS 対策（テンプレート自動エスケープ）
   - 入力値検証

3. **通信保護**
   - HTTPS 強制
   - セキュアヘッダー設定
   - CORS 設定

4. **設定セキュリティ**
   - 環境変数による機密情報管理
   - デバッグモード制御
   - 適切なログレベル

### セキュリティチェックリスト

- [ ] SECRET_KEY の環境変数化
- [ ] DATABASE_URL の環境変数化
- [ ] ALLOWED_HOSTS の適切な設定
- [ ] DEBUG=False in production
- [ ] SSL/TLS 証明書設定
- [ ] セキュリティヘッダー設定
- [ ] ログ設定の見直し
- [ ] 依存関係の脆弱性チェック

## パフォーマンス

### キャッシュ戦略

```python
# Redis キャッシュ階層
┌─────────────────┐
│ Application     │ ← Django Cache Framework
│ Cache           │   (ビュー、クエリセット)
├─────────────────┤
│ Session Cache   │ ← セッションデータ
├─────────────────┤
│ Celery Broker   │ ← タスクキュー
└─────────────────┘
```

### データベース最適化

1. **インデックス戦略**
   ```sql
   -- よく検索される列にインデックス
   CREATE INDEX idx_race_date ON races_race(race_date);
   CREATE INDEX idx_horse_name ON horses_horse(name);
   ```

2. **クエリ最適化**
   ```python
   # N+1 問題回避
   races = Race.objects.select_related('venue').prefetch_related('entries__horse')
   ```

3. **ページネーション**
   ```python
   # 大量データの効率的な取得
   paginator = Paginator(queryset, 25)
   ```

### 非同期処理

```python
# Celery タスク分類
┌─────────────────┐
│ High Priority   │ ← リアルタイム通知
├─────────────────┤
│ Medium Priority │ ← データ処理
├─────────────────┤
│ Low Priority    │ ← バックアップ、レポート
└─────────────────┘
```

## スケーラビリティ

### 水平スケーリング

1. **Webサーバー**
   - ロードバランサー (Nginx)
   - 複数のGunicornワーカー
   - セッションレス設計

2. **データベース**
   - 読み取り専用レプリカ
   - コネクションプーリング
   - パーティショニング

3. **キャッシュ**
   - Redis クラスター
   - CDN による静的ファイル配信

### 監視・メトリクス

```python
# 監視項目
- Response Time
- Error Rate  
- CPU/Memory Usage
- Database Performance
- Cache Hit Rate
- Celery Queue Length
```

## デプロイメント

### 環境構成

```
┌─────────────────┐
│ Production      │ ← Docker Swarm / Kubernetes
├─────────────────┤
│ Staging         │ ← Docker Compose
├─────────────────┤
│ Development     │ ← Local Environment
└─────────────────┘
```

### CI/CD パイプライン

```yaml
# GitHub Actions例
1. Code Checkout
2. Test Execution
3. Code Quality Check
4. Security Scan
5. Build Docker Image
6. Deploy to Staging
7. Integration Test
8. Deploy to Production
```

## 機械学習パイプライン

### モデル学習フロー

```
Raw Data → Feature Engineering → Model Training → Validation → Deployment
    ↑             ↓                    ↓              ↓          ↓
Data QC    Feature Store        Model Registry   A/B Test   Monitoring
```

### 特徴量エンジニアリング

1. **基本特徴量**
   - 馬の基本情報（年齢、性別、体重）
   - 騎手情報（経験、勝率）
   - レース条件（距離、馬場、天候）

2. **統計特徴量**
   - 過去N戦の成績
   - 相性データ（騎手×馬、馬×競馬場）
   - トレンド情報

3. **高次特徴量**
   - 血統指数
   - クラス指数
   - スピード指数

### モデル管理

```python
# モデルバージョン管理
ml_models/
├── trained/
│   ├── xgboost_v1.0.pkl
│   ├── lightgbm_v1.0.pkl
│   └── ensemble_v1.0.pkl
├── experiments/
│   └── experiment_2024_01/
└── datasets/
    ├── features_v1.csv
    └── labels_v1.csv
```

## 今後の拡張予定

### 短期（3ヶ月）
- [ ] リアルタイム予測API
- [ ] モバイルアプリ対応
- [ ] 高度な可視化ダッシュボード
- [ ] A/Bテストフレームワーク

### 中期（6ヶ月）
- [ ] マルチクラウド対応
- [ ] ストリーミングデータ処理
- [ ] 深層学習モデル導入
- [ ] 自動モデル更新

### 長期（1年）
- [ ] マイクロサービス化
- [ ] GraphQL API
- [ ] 機械学習MLOps完全自動化
- [ ] 国際対応（海外競馬）
