from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import AuditLog
from .serializers import AuditLogSerializer


class IsAdminUser(permissions.BasePermission):
    """صلاحية للمشرفين فقط"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """عرض سجلات المراجعة (للمشرفين فقط)"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'resource_type', 'user']
    search_fields = ['resource_id', 'user__phone', 'user__first_name', 'user__last_name']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """تطبيق فلاتر إضافية"""
        queryset = AuditLog.objects.select_related('user').all()
        
        # فلتر حسب الفترة الزمنية
        days = self.request.query_params.get('days')
        if days:
            try:
                days = int(days)
                since = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(timestamp__gte=since)
            except (ValueError, TypeError):
                pass
        
        # فلتر حسب المستخدم
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات سريعة عن السجلات"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = {
            'total': AuditLog.objects.count(),
            'today': AuditLog.objects.filter(timestamp__gte=today_start).count(),
            'by_action': AuditLog.objects.values('action').annotate(
                count=models.Count('id')
            ).order_by('-count'),
            'by_resource': AuditLog.objects.values('resource_type').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10],
        }
        
        return Response(stats)