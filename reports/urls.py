from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', views.ReportStatisticsView.as_view(), name='report-statistics'),
    path('stats/', views.ReportStatisticsView.as_view(), name='report-stats'),  # alias
]