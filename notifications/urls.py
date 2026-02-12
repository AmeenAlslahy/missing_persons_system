from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'preferences', views.NotificationPreferenceViewSet, basename='preference')
router.register(r'push-tokens', views.PushNotificationTokenViewSet, basename='push-token')
router.register(r'admin/notifications', views.AdminNotificationViewSet, basename='admin-notification')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.NotificationStatisticsView.as_view(), name='notification-stats'),
]