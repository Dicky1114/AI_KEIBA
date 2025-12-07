# Create your views here.
from django.views import View
from django.contrib import messages
from ..forms import LoginForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

class LoginView(View):
    template_name = 'app_folder/login.html'

    def get(self, request):
        """ログイン画面表示時の処理"""
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        """ログインフォームのPOST処理"""
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "ログイン成功")
                return redirect('app_folder:dashboard')
            else:
                messages.error(request, "ログインエラー")
        else:
            messages.error(request, "ログインエラー")
        return render(request, self.template_name, {'form': form})
    
login_view = LoginView.as_view()