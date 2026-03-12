from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'admin/notifications', views.AdminNotificationViewSet, basename='admin-notification')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.NotificationStatisticsView.as_view(), name='notification-stats'),
    path('preferences/', views.NotificationPreferencesView.as_view(), name='notification-preferences'),
]