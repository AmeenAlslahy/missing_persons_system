# admin_dashboard/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from accounts.models import User


class AdminStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/admin-dashboard/login/'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(self.login_url)
        messages.error(self.request, _('ليس لديك صلاحية الوصول إلى هذه الصفحة'))
        return redirect('admin_dashboard:index')


class DashboardView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard.html'


class UserManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/users.html'


class UserDetailView(AdminStaffRequiredMixin, TemplateView):  # ✅ كلاس جديد
    """عرض تفاصيل مستخدم محدد"""
    template_name = 'admin_dashboard/user_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, id=user_id)
        context['target_user'] = user
        context['page_title'] = f'تفاصيل المستخدم: {user.full_name}'
        return context


class ReportManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/reports.html'


class ReportDetailView(AdminStaffRequiredMixin, TemplateView):  # ✅ كلاس جديد
    """عرض تفاصيل بلاغ محدد"""
    template_name = 'admin_dashboard/report_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_id = self.kwargs.get('report_id')
        context['report_id'] = report_id
        context['page_title'] = f'تفاصيل البلاغ #{report_id}'
        return context


class MatchManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/matching.html'


class MatchDetailView(AdminStaffRequiredMixin, TemplateView):  # ✅ كلاس جديد
    """عرض تفاصيل مطابقة محددة"""
    template_name = 'admin_dashboard/match_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match_id = self.kwargs.get('match_id')
        context['match_id'] = match_id
        context['page_title'] = f'تفاصيل المطابقة #{match_id}'
        return context


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
        
        # يمكن أن يكون username هو phone أو email
        user = None
        if '@' in username:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, phone=user_obj.phone, password=password)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(request, phone=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            next_url = request.GET.get('next', 'admin_dashboard:index')
            messages.success(request, _('تم تسجيل الدخول بنجاح'))
            return redirect(next_url)
        else:
            messages.error(request, _('بيانات الدخول غير صحيحة أو ليس لديك صلاحية'))
            return render(request, self.template_name)


class AdminLogoutView(View):  # ✅ كلاس جديد
    """تسجيل الخروج من لوحة التحكم"""
    
    def get(self, request):
        logout(request)
        messages.success(request, _('تم تسجيل الخروج بنجاح'))
        return redirect('admin_dashboard:login')
    
    def post(self, request):
        return self.get(request)