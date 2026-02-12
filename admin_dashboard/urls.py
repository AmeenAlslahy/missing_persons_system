from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='index'),
    path('login/', views.AdminLoginView.as_view(), name='login'),
    path('users/', views.UserManagementView.as_view(), name='users'),
    path('reports/', views.ReportManagementView.as_view(), name='reports'),
    path('matches/', views.MatchManagementView.as_view(), name='matches'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('audit-log/', views.AuditLogView.as_view(), name='audit_log'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('monitoring/', views.MonitoringView.as_view(), name='monitoring'),
    path('notifications/', views.NotificationBroadcastView.as_view(), name='notifications'),
]
