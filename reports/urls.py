from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', views.ReportStatisticsView.as_view(), name='report-statistics'),
    path('stats/', views.ReportStatisticsView.as_view(), name='report-stats'),  # alias
    path('search-persons/', views.SearchPersonsView.as_view(), name='search-persons'),
    path('persons/<uuid:person_id>/report/', views.CreateReportFromPersonView.as_view(), name='create-report-from-person'),
]