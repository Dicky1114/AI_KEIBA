# account/views.py
from django.contrib.auth.views import LogoutView

class CustomeLogoutView(LogoutView):
    def get_next_page(self):
        # リクエストのURLによってリダイレクト先を変更
        if self.request.path.startswith('/admin/'):
            # 管理画面の場合
            return '/admin/login/'
        else:
            # フロントエンド画面の場合
            return '/app_folder/login/'

        
logout_view = CustomeLogoutView.as_view()