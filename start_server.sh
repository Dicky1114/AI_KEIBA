#!/bin/bash

# 競馬予測システム起動スクリプト
echo "🐎 競馬予測システムを起動中..."

# ディレクトリ移動
cd /Users/hojo/Desktop/01_GitHub/50_競馬予測/keiba_prediction

# 仮想環境のPythonを使用してサーバー起動
echo "🚀 Django開発サーバーを起動します..."
/Users/hojo/Desktop/01_GitHub/50_競馬予測/venv/bin/python manage.py runserver 8000

echo ""
echo "✅ サーバーが起動しました！"
echo "🌐 フロントエンド: http://localhost:8000/"
echo "🔧 管理画面: http://localhost:8000/admin/"
echo "📊 API: http://localhost:8000/api/v1/"
echo ""
echo "ログイン情報:"
echo "  ユーザー名: admin"
echo "  パスワード: admin123"
echo ""
echo "サーバーを停止するには Ctrl+C を押してください"
