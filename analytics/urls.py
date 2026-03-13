from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# إنشاء router رئيسي
router = DefaultRouter()
router.register(r'daily-stats', views.DailyStatsViewSet, basename='daily-stats')
router.register(r'performance-metrics', views.PerformanceMetricsViewSet, basename='performance-metrics')
router.register(r'reports', views.AnalyticsReportViewSet, basename='analytics-report')
router.register(r'widgets', views.DashboardWidgetViewSet, basename='dashboard-widget')

# مسارات API
urlpatterns = [
    # تضمين مسارات router
    path('', include(router.urls)),
    
    # مسارات إضافية
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('generate-report/', views.GenerateReportView.as_view(), name='generate-report'),
    path('overall-stats/', views.AnalyticsStatisticsView.as_view(), name='overall-stats'),
    path('stats/', views.AnalyticsStatisticsView.as_view(), name='analytics-stats'),  # alias
]

# تحديد اسم التطبيق للمسارات العكسية
app_name = 'analytics'