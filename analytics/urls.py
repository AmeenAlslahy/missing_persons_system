from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.AnalyticsReportViewSet, basename='analytics-report')
router.register(r'widgets', views.DashboardWidgetViewSet, basename='dashboard-widget')
router.register(r'daily-stats', views.DailyStatsViewSet, basename='daily-stats')
router.register(r'performance-metrics', views.PerformanceMetricsViewSet, basename='performance-metrics')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('generate-report/', views.GenerateReportView.as_view(), name='generate-report'),
    path('stats/', views.AnalyticsStatisticsView.as_view(), name='overall-stats'),
]