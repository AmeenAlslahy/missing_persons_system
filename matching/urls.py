from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'matches', views.MatchResultViewSet, basename='match')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', views.MatchStatisticsView.as_view(), name='matching-statistics'),
    path('stats/', views.MatchStatisticsView.as_view(), name='matching-stats'),  # alias
]

app_name = 'matching'