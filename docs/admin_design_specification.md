# Django管理画面カスタマイズ詳細設計書

## 概要

競馬予測システムのDjango管理画面を、モダンなUI/UXデザインにカスタマイズした設計書です。ヘッダー、サイドバー、メインコンテンツエリアを適切に分離し、レスポンシブ対応を実装しています。

## アーキテクチャ概要

### ファイル構成

```
config/
├── templates/admin/
│   ├── base.html              # Django管理画面のベーステンプレート
│   └── base_site.html         # カスタム管理画面テンプレート
├── static/
│   ├── css/
│   │   └── admin.css          # 管理画面専用CSS
│   └── js/
│       └── admin.js           # 管理画面専用JavaScript
└── settings/
    ├── base.py                # ベース設定
    ├── development.py         # 開発環境設定
    └── production.py          # 本番環境設定
```

## コンポーネント設計

### 1. ヘッダーコンポーネント (`premium-header`)

**役割**: 固定ヘッダーとして常に表示され、ブランディングとナビゲーション機能を提供

**主要要素**:
- ブランドロゴ（馬のアイコン + テキスト）
- ハンバーガーメニューボタン
- ユーザープロファイル
- アクションボタン（フロントサイト、ログアウト）

**CSS クラス**:
```css
.premium-header          # 固定ヘッダーコンテナ
.header-container        # ヘッダー内容のコンテナ
.brand-section          # ブランドエリア
.brand-link             # ブランドリンク
.brand-icon-wrapper     # アイコンラッパー
.brand-icon             # ブランドアイコン
.icon-glow              # アイコングロー効果
.brand-title            # ブランドタイトル
.brand-subtitle         # ブランドサブタイトル
.header-controls        # ヘッダーコントロールエリア
.hamburger-menu         # ハンバーガーメニューボタン
.user-profile           # ユーザープロファイル
.avatar                 # アバターアイコン
.user-details           # ユーザー詳細
.user-name              # ユーザー名
.user-role              # ユーザーロール
.header-actions         # ヘッダーアクション
.action-btn             # アクションボタン
```

**JavaScript機能**:
- ハンバーガーメニューのクリックイベント
- サイドバーの表示/非表示制御

### 2. サイドバーコンポーネント (`premium-sidebar`)

**役割**: デフォルトで非表示、ハンバーガーメニューで表示されるナビゲーション

**主要要素**:
- サイドバーヘッダー
- ナビゲーショングループ
- システムステータス
- モバイルオーバーレイ

**CSS クラス**:
```css
.premium-sidebar        # サイドバーコンテナ
.sidebar-header         # サイドバーヘッダー
.sidebar-brand          # サイドバーブランド
.sidebar-toggle         # サイドバートグルボタン
.sidebar-content        # サイドバーコンテンツ
.nav-group              # ナビゲーショングループ
.nav-group-title        # グループタイトル
.nav-list               # ナビゲーションリスト
.nav-item               # ナビゲーションアイテム
.nav-link               # ナビゲーションリンク
.nav-icon               # ナビゲーションアイコン
.nav-text               # ナビゲーションテキスト
.nav-badge              # ナビゲーションバッジ
.nav-status             # ナビゲーションステータス
.nav-indicator          # ナビゲーションインジケーター
.sidebar-footer         # サイドバーフッター
.system-status          # システムステータス
.status-item            # ステータスアイテム
.status-indicator       # ステータスインジケーター
.system-info            # システム情報
.mobile-overlay-backdrop # モバイルオーバーレイ
```

**JavaScript機能**:
- サイドバーの表示/非表示制御
- モバイル対応（オーバーレイ表示）
- タッチジェスチャー対応
- アクティブナビゲーションのハイライト

### 3. メインコンテンツエリア (`#content`)

**役割**: Django管理画面のメインコンテンツを表示

**CSS クラス**:
```css
#content                # メインコンテンツエリア
.sidebar-collapsed #content  # サイドバー非表示時のコンテンツ
.sidebar-show #content       # サイドバー表示時のコンテンツ
.sidebar-overlay #content    # オーバーレイ時のコンテンツ
```

**レイアウト制御**:
- サイドバー非表示時: 全幅表示
- サイドバー表示時: 左マージンでサイドバー分を確保
- モバイル時: 常に全幅表示

### 4. フッターコンポーネント (`premium-footer`)

**役割**: システム情報とリンクを表示

**CSS クラス**:
```css
.premium-footer         # フッターコンテナ
.footer-container       # フッター内容のコンテナ
.footer-content         # フッターコンテンツ
.footer-brand           # フッターブランド
.footer-info            # フッター情報
.footer-links           # フッターリンク
```

## レスポンシブデザイン

### ブレークポイント

```css
/* デスクトップ */
@media (min-width: 1201px) {
    .premium-sidebar { transform: translateX(0); }
}

/* タブレット */
@media (max-width: 1200px) {
    .premium-sidebar { transform: translateX(-100%); }
    #content { margin-left: 0; }
}

/* モバイル */
@media (max-width: 768px) {
    .user-profile { display: none; }
    #content { padding: 1.5rem; }
}
```

### サイドバー表示制御

1. **デスクトップ**: サイドバー表示時はメインコンテンツが右にシフト
2. **タブレット/モバイル**: サイドバーはオーバーレイ表示、メインコンテンツは常に全幅

## JavaScript機能詳細

### 状態管理

```javascript
let sidebarState = {
    isCollapsed: true,      // サイドバーが折りたたまれているか
    isMobile: false,        // モバイル表示かどうか
    autoHideTimer: null,    // 自動非表示タイマー
    isOverlay: false,       // オーバーレイ表示かどうか
    isShowing: false        // サイドバーが表示されているか
};
```

### 主要機能

1. **サイドバー制御**
   - `showSidebar()`: サイドバー表示
   - `hideSidebar()`: サイドバー非表示
   - `toggleSidebarWithHamburger()`: ハンバーガーメニューでの切り替え

2. **レスポンシブ対応**
   - `updateSidebarState()`: 画面サイズ変更時の状態更新
   - `toggleMobileSidebar()`: モバイルサイドバー制御

3. **ユーザーインタラクション**
   - `highlightActiveNavigation()`: アクティブナビゲーションのハイライト
   - `handleSwipeGesture()`: タッチジェスチャー対応

## CSS変数システム

### カラーパレット

```css
:root {
    /* グラデーション */
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --accent-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    
    /* 背景色 */
    --bg-primary: #0f1419;
    --bg-secondary: #1a1f2e;
    --bg-tertiary: #252d3f;
    
    /* テキスト色 */
    --text-primary: #ffffff;
    --text-secondary: #a0aec0;
    --text-muted: #718096;
    
    /* レイアウト */
    --sidebar-width: 320px;
    --header-height: 88px;
}
```

## Django統合

### テンプレート継承

```django
{% extends "admin/base.html" %}
{% load static %}

{% block title %}{% if subtitle %}{{ subtitle }} | {% endif %}{{ title }} | 競馬予測システム{% endblock %}

{% block branding %}
    <!-- カスタムヘッダー -->
{% endblock %}

{% block nav-global %}
    <!-- カスタムサイドバー -->
{% endblock %}

{% block extrastyle %}
    <!-- 外部CSS読み込み -->
{% endblock %}

{% block extrajs %}
    <!-- 外部JavaScript読み込み -->
{% endblock %}
```

### 静的ファイル管理

- CSS: `config/static/css/admin.css`
- JavaScript: `config/static/js/admin.js`
- フォント: Google Fonts (Inter, JetBrains Mono)
- アイコン: Font Awesome 6.5.0

## パフォーマンス最適化

### CSS最適化

1. **CSS変数使用**: 一貫性のあるデザインシステム
2. **モジュラー設計**: コンポーネント単位でのスタイル管理
3. **レスポンシブ画像**: 適切な画像サイズとフォーマット

### JavaScript最適化

1. **イベントデリゲーション**: 効率的なイベント処理
2. **状態管理**: 最小限の状態変更
3. **メモリリーク防止**: 適切なイベントリスナーの削除

## アクセシビリティ

### キーボードナビゲーション

- Tabキーでのナビゲーション
- Enterキーでのアクション実行
- Escapeキーでのモーダル閉じる

### スクリーンリーダー対応

- 適切なARIAラベル
- セマンティックなHTML構造
- フォーカス管理

## ブラウザサポート

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 今後の拡張性

### 追加可能な機能

1. **テーマ切り替え**: ダーク/ライトテーマ
2. **多言語対応**: i18n対応
3. **カスタムダッシュボード**: ユーザー定義ダッシュボード
4. **リアルタイム通知**: WebSocket対応

### 保守性

1. **モジュラー設計**: コンポーネント単位での修正
2. **ドキュメント化**: 詳細なコメントとドキュメント
3. **テスト対応**: 単体テストとE2Eテストの実装

## セキュリティ考慮事項

1. **XSS対策**: 適切なエスケープ処理
2. **CSRF対策**: Django標準のCSRFトークン使用
3. **権限管理**: Django標準の権限システム使用

## まとめ

この設計により、Django管理画面をモダンなUI/UXにカスタマイズし、保守性と拡張性を確保しています。コンポーネント分離により、各機能を独立して修正・拡張でき、レスポンシブデザインにより様々なデバイスで最適な表示を実現しています。
