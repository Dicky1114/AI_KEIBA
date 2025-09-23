"""
共通ビュー
"""
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class HomeView(TemplateView):
    """
    ホームページビュー
    """
    template_name = 'frontend/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': '競馬予測システム',
            'page_description': 'AIを活用した競馬予測システムです。',
        })
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    ダッシュボードビュー
    """
    template_name = 'frontend/dashboard.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'ダッシュボード',
            'user': self.request.user,
        })
        return context
