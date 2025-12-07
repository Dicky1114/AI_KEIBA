# Create your views here.
from django.views import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'app_folder/dashboard.html')
    
dashboard_view = DashboardView.as_view()