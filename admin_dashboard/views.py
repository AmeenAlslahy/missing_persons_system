from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import authenticate, login

class AdminStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/admin-dashboard/login/'
    
    def test_func(self):
        return self.request.user.is_staff

class DashboardView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard.html'

class UserManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/users.html'

class ReportManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/reports.html'

class MatchManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/matching.html'

class AnalyticsView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/analytics.html'

class AuditLogView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/audit-log.html'

class SettingsView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/settings.html'

class MonitoringView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/monitoring.html'

class NotificationBroadcastView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/notifications.html'


class AdminLoginView(View):
    template_name = 'admin_dashboard/login.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect('admin_dashboard:index')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            next_url = request.GET.get('next', 'admin_dashboard:index')
            return redirect(next_url)
        else:
            return render(request, self.template_name, {'error': 'بيانات الدخول غير صحيحة أو ليس لديك صلاحية'})
