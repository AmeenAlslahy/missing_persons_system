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
    """ميكسين للتحقق من صلاحية المشرف"""
    login_url = '/admin-dashboard/login/'
    redirect_field_name = 'next'
    
    def test_func(self):
        """التحقق من أن المستخدم مشرف"""
        return self.request.user.is_authenticated and self.request.user.is_staff
    
    def handle_no_permission(self):
        """معالجة عدم وجود الصلاحية"""
        if not self.request.user.is_authenticated:
            # المستخدم غير مسجل دخول - إرسال إلى صفحة تسجيل الدخول
            return redirect(f"{self.login_url}?next={self.request.path}")
        
        # المستخدم مسجل دخول ولكن ليس مشرفاً
        messages.error(self.request, _('ليس لديك صلاحية الوصول إلى لوحة التحكم'))
        # تغيير المسار لتجنب حلقة إعادة التوجيه
        return redirect('admin_dashboard:login')


class DashboardView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('لوحة التحكم الرئيسية')
        return context


class UserManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/users.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('إدارة المستخدمين')
        return context


class UserDetailView(AdminStaffRequiredMixin, TemplateView):
    """عرض تفاصيل مستخدم محدد"""
    template_name = 'admin_dashboard/user_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            context['target_user'] = user
            context['page_title'] = f'تفاصيل المستخدم: {user.full_name}'
        except User.DoesNotExist:
            context['target_user'] = None
            context['page_title'] = _('المستخدم غير موجود')
            messages.error(self.request, _('المستخدم المطلوب غير موجود'))
        return context


class ReportManagementView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('إدارة البلاغات')
        return context


class ReportDetailView(AdminStaffRequiredMixin, TemplateView):
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('إدارة المطابقات')
        return context


class MatchDetailView(AdminStaffRequiredMixin, TemplateView):
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('التحليلات والإحصائيات')
        return context


class AuditLogView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/audit-log.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('سجل العمليات')
        return context


class SettingsView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('إعدادات النظام')
        return context


class MonitoringView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/monitoring.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('مراقبة النظام')
        return context


class NotificationBroadcastView(AdminStaffRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('الإشعارات')
        return context


class AdminLoginView(View):
    template_name = 'admin_dashboard/login.html'

    def get(self, request):
        # إذا كان المستخدم مسجل دخول بالفعل وهو مشرف، حوله إلى لوحة التحكم
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
        
        if user is not None:
            if user.is_staff:
                login(request, user)
                next_url = request.GET.get('next', 'admin_dashboard:index')
                messages.success(request, _('تم تسجيل الدخول بنجاح'))
                return redirect(next_url)
            else:
                messages.error(request, _('ليس لديك صلاحية الوصول إلى لوحة التحكم'))
        else:
            messages.error(request, _('بيانات الدخول غير صحيحة'))
        
        return render(request, self.template_name)


class AdminLogoutView(View):
    """تسجيل الخروج من لوحة التحكم"""
    
    def get(self, request):
        logout(request)
        messages.success(request, _('تم تسجيل الخروج بنجاح'))
        return redirect('admin_dashboard:login')
    
    def post(self, request):
        return self.get(request)