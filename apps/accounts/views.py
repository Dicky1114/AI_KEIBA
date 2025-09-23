"""
Accounts views
"""
from django.shortcuts import render, redirect
from django.views.generic import CreateView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse_lazy
from .models import CustomUser, UserPreference
from .forms import CustomUserCreationForm, UserProfileForm


class RegisterView(CreateView):
    """
    ユーザー登録ビュー
    """
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('core:dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 自動ログイン
        login(self.request, self.object)
        # ユーザー設定の初期作成
        UserPreference.objects.create(user=self.object)
        messages.success(self.request, 'アカウントが正常に作成されました！')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    プロフィール表示ビュー
    """
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user': self.request.user,
            'preferences': getattr(self.request.user, 'preferences', None),
        })
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """
    プロフィール編集ビュー
    """
    model = CustomUser
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, 'プロフィールが更新されました。')
        return super().form_valid(form)
