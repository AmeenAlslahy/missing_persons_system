# admin_dashboard/urls.py
from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.DashboardView.as_view(), name='index'),
    path('index/', views.DashboardView.as_view(), name='index-alt'),
    
    # المصادقة
    path('login/', views.AdminLoginView.as_view(), name='login'),
    path('logout/', views.AdminLogoutView.as_view(), name='logout'),
    
    # إدارة المستخدمين
    path('users/', views.UserManagementView.as_view(), name='users'),
    path('users/<int:user_id>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # إدارة البلاغات
    path('reports/', views.ReportManagementView.as_view(), name='reports'),
    path('reports/<uuid:report_id>/', views.ReportDetailView.as_view(), name='report-detail'),
    
    # إدارة المطابقات
    path('matches/', views.MatchManagementView.as_view(), name='matches'),
    path('matches/<uuid:match_id>/', views.MatchDetailView.as_view(), name='match-detail'),
    
    # التحليلات
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    
    # سجل العمليات
    path('audit-log/', views.AuditLogView.as_view(), name='audit_log'),
    
    # إعدادات النظام
    path('settings/', views.SettingsView.as_view(), name='settings'),
    
    # مراقبة النظام
    path('monitoring/', views.MonitoringView.as_view(), name='monitoring'),
    
    # الإشعارات
    path('notifications/', views.NotificationBroadcastView.as_view(), name='notifications'),
]