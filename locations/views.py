from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
import hashlib

from .models import Governorate, District, Uzlah
from .serializers import (
    GovernorateSerializer, GovernorateDetailSerializer,
    DistrictSerializer, DistrictDetailSerializer,
    UzlahSerializer
)


class LocationPagination(PageNumberPagination):
    """Pagination مخصص للمواقع"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GovernorateViewSet(viewsets.ModelViewSet):
    """
    ViewSet للمحافظات
    """
    queryset = Governorate.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = GovernorateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = LocationPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    ordering_fields = ['order', 'name', 'population', 'area']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GovernorateDetailSerializer
        return GovernorateSerializer
    
    def get_cache_key(self, prefix, identifier, request):
        """إنشاء مفتاح كاش مع مراعاة معاملات البحث"""
        base_key = f"{prefix}_{identifier}"
        # إضافة معاملات البحث إلى المفتاح
        query_params = dict(request.GET.items())
        if query_params:
            param_hash = hashlib.md5(str(sorted(query_params.items())).encode()).hexdigest()[:8]
            base_key = f"{base_key}_{param_hash}"
        return base_key
    
    @method_decorator(cache_page(60 * 15))  # كاش لمدة 15 دقيقة
    @method_decorator(vary_on_headers('Authorization'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def districts(self, request, pk=None):
        """
        جلب جميع المديريات في محافظة محددة مع نظام كاش مطور
        """
        governorate = self.get_object()
        
        # استخدام مفتاح كاش ديناميكي
        cache_key = self.get_cache_key('districts_gov', pk, request)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        districts = governorate.districts.filter(is_active=True).order_by('order', 'name')
        serializer = DistrictSerializer(districts, many=True, context={'request': request})
        
        # تخزين في الكاش مع وقت انتهاء أقصر (5 دقائق)
        cache.set(cache_key, serializer.data, 60 * 5)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """إحصائيات سريعة عن المناطق"""
        stats = {
            'total_governorates': Governorate.objects.filter(is_active=True).count(),
            'total_districts': District.objects.filter(is_active=True).count(),
            'total_uzlahs': Uzlah.objects.filter(is_active=True).count(),
            'most_populated': Governorate.objects.filter(
                is_active=True, population__isnull=False
            ).order_by('-population').values('name_ar', 'population')[:5],
            'largest_area': Governorate.objects.filter(
                is_active=True, area__isnull=False
            ).order_by('-area').values('name_ar', 'area')[:5],
        }
        return Response(stats)


class DistrictViewSet(viewsets.ModelViewSet):
    """
    ViewSet للمديريات
    """
    queryset = District.objects.filter(is_active=True).order_by('governorate__order', 'order', 'name')
    serializer_class = DistrictSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = LocationPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['governorate', 'is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    ordering_fields = ['order', 'name', 'population']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DistrictDetailSerializer
        return DistrictSerializer
    
    def get_cache_key(self, prefix, identifier, request):
        base_key = f"{prefix}_{identifier}"
        query_params = dict(request.GET.items())
        if query_params:
            param_hash = hashlib.md5(str(sorted(query_params.items())).encode()).hexdigest()[:8]
            base_key = f"{base_key}_{param_hash}"
        return base_key
        
    @action(detail=True, methods=['get'])
    def uzlahs(self, request, pk=None):
        """
        جلب جميع العزل في مديرية محددة
        """
        district = self.get_object()
        
        cache_key = self.get_cache_key('uzlahs_dist', pk, request)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        uzlahs = district.uzlahs.filter(is_active=True).order_by('order', 'name')
        serializer = UzlahSerializer(uzlahs, many=True, context={'request': request})
        
        cache.set(cache_key, serializer.data, 60 * 5)
        return Response(serializer.data)


class UzlahViewSet(viewsets.ModelViewSet):
    """
    ViewSet للعزل
    """
    queryset = Uzlah.objects.filter(is_active=True).order_by('district__governorate__order', 'district__order', 'order', 'name')
    serializer_class = UzlahSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = LocationPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['district', 'district__governorate', 'is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    ordering_fields = ['order', 'name', 'population']