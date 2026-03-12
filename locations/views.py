from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from .models import Governorate, District, Uzlah
from .serializers import (
    GovernorateSerializer, GovernorateDetailSerializer,
    DistrictSerializer, DistrictDetailSerializer,
    UzlahSerializer
)


class GovernorateViewSet(viewsets.ModelViewSet):
    """
    ViewSet للمحافظات
    """
    queryset = Governorate.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = GovernorateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    ordering_fields = ['order', 'name', 'population', 'area']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GovernorateDetailSerializer
        return GovernorateSerializer
    
    @method_decorator(cache_page(60 * 15))  # كاش لمدة 15 دقيقة
    @method_decorator(vary_on_headers('Authorization'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def districts(self, request, pk=None):
        """
        جلب جميع المديريات في محافظة محددة
        """
        governorate = self.get_object()
        districts = governorate.districts.filter(is_active=True).order_by('order', 'name')
        
        # استخدام الكاش
        cache_key = f'districts_gov_{pk}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        serializer = DistrictSerializer(districts, many=True, context={'request': request})
        cache.set(cache_key, serializer.data, 60 * 10)  # كاش لمدة 10 دقائق
        return Response(serializer.data)


class DistrictViewSet(viewsets.ModelViewSet):
    """
    ViewSet للمديريات
    """
    queryset = District.objects.filter(is_active=True).order_by('governorate__order', 'order', 'name')
    serializer_class = DistrictSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['governorate', 'is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    ordering_fields = ['order', 'name', 'population']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DistrictDetailSerializer
        return DistrictSerializer
    
    @action(detail=True, methods=['get'])
    def uzlahs(self, request, pk=None):
        """
        جلب جميع العزل في مديرية محددة
        """
        district = self.get_object()
        uzlahs = district.uzlahs.filter(is_active=True).order_by('order', 'name')
        
        # استخدام الكاش
        cache_key = f'uzlahs_dist_{pk}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        serializer = UzlahSerializer(uzlahs, many=True, context={'request': request})
        cache.set(cache_key, serializer.data, 60 * 10)  # كاش لمدة 10 دقائق
        return Response(serializer.data)


class UzlahViewSet(viewsets.ModelViewSet):
    """
    ViewSet للعزل
    """
    queryset = Uzlah.objects.filter(is_active=True).order_by('district__governorate__order', 'district__order', 'order', 'name')
    serializer_class = UzlahSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['district', 'district__governorate', 'is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    ordering_fields = ['order', 'name', 'population']