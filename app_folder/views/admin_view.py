# 修正済み
# =========================================================
# # 概要       ：管理画面のメイン処理
# 改訂履歴      :2025/04/29 初版
# =========================================================

# ライブラリ
from django.views import View
from django.shortcuts import render

# メイン画面用クラス
class AdminView(View):
    """ メイン画面用クラス
        概要：
            様々な機能に遷移するためのメニュー画面。
        引数:
            View：Djangoのクラスベースビューの親クラス
        関数:
            get():
                初期イベント
    """
    # ホーム画面
    def get(self, request):
        """ 初期イベント
            概要：
                Index.html画面起動時のGetイベント。
            戻り値:
                HttpResponse: 処理結果に応じたHTTPレスポンスオブジェクト。
        """
        return render(request, "admin/index.html")
