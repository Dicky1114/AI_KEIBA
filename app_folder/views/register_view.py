# Create your views here.
from django.views import View
from django.contrib import messages
from ..forms import RegisterForm
from django.shortcuts import render
from django.contrib.auth import login

class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'app_folder/register.html', {'form': form})

    # POSTリクエストに対する処理
    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # ユーザーをログインさせる
            messages.success(request, '会員登録が成功しました！')
            return render(request, 'app_folder/register.html', {'form': form, 'success': True})  # 成功フラグを渡す
        else:
            messages.error(request, '登録に失敗しました。エラーを確認してください。')
            return render(request, 'app_folder/register.html', {'form': form})

register_view = RegisterView.as_view()