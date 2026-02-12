from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'matches', views.MatchResultViewSet, basename='match')
router.register(r'config', views.MatchingConfigViewSet)
router.register(r'embeddings', views.FaceEmbeddingViewSet, basename='embedding')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.MatchStatisticsView.as_view(), name='matching-stats'),
]