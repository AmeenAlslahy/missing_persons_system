from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'governorates', views.GovernorateViewSet, basename='governorate')
router.register(r'districts', views.DistrictViewSet, basename='district')
router.register(r'uzlahs', views.UzlahViewSet, basename='uzlah')

urlpatterns = [
    path('', include(router.urls)),
]

app_name = 'locations'