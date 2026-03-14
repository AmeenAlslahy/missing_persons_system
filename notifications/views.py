from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.db import connection

from django.utils.translation import gettext_lazy as _
from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationStatsSerializer, MarkAsReadSerializer,
    NotificationPreferenceSerializer
)
from .services import NotificationService


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet للإشعارات - قراءة فقط"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'priority_level', 'is_read']
    
    def get_queryset(self):
        """تصفية الإشعارات للمستخدم الحالي فقط"""
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """تحديد إشعارات كمقروءة"""
        serializer = MarkAsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user
        
        if data.get('read_all'):
            # تحديد كل الإشعارات كمقروءة
            notifications = Notification.objects.filter(
                user=user,
                is_read=False
            )
            count = notifications.count()
            for notification in notifications:
                notification.mark_as_read()
        else:
            # تحديد إشعارات محددة كمقروءة
            notifications = Notification.objects.filter(
                user=user,
                notification_id__in=data['notification_ids']
            )
            count = notifications.count()
            for notification in notifications:
                notification.mark_as_read()
        
        return Response({
            'message': f'تم تحديد {count} إشعار كمقروء',
            'count': count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """عدد الإشعارات غير المقروءة"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return Response({'count': count})
    
    @action(detail=False, methods=['delete'])
    def clear_read(self, request):
        """حذف الإشعارات المقروءة"""
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=True
        )
        
        count = notifications.count()
        notifications.delete()
        
        return Response({
            'message': f'تم حذف {count} إشعار مقروء',
            'count': count
        })


class AdminNotificationViewSet(viewsets.ModelViewSet):
    """ViewSet للإشعارات (للمشرفين)"""
    permission_classes = [IsAdminUser]
    queryset = Notification.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def create(self, request, *args, **kwargs):
        """إنشاء إشعارات جماعية"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # استخدام خدمة الإشعارات
        service = NotificationService()
        notifications = service.send_bulk_notification(
            notification_type=data['notification_type'],
            title=data['title'],
            message=data['message'],
            user_ids=data.get('user_ids'),
            priority=data['priority_level'],
            action_required=data['action_required'],
            action_url=data.get('action_url', ''),
            action_text=data.get('action_text', ''),
            expiry_days=data['expiry_days']
        )
        
        return Response({
            'message': f'تم إرسال {len(notifications)} إشعار',
            'count': len(notifications)
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات الإشعارات"""
        # إحصائيات عامة
        total = Notification.objects.count()
        unread = Notification.objects.filter(is_read=False).count()
        urgent = Notification.objects.filter(priority_level='urgent').count()
        
        # حسب النوع
        by_type = Notification.objects.values('notification_type').annotate(
            count=Count('notification_id')
        ).order_by('-count')
        
        # حسب اليوم (آخر 7 أيام) - بطريقة متوافقة مع SQL Server
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        # استخدام TruncDate بدلاً من extra
        from django.db.models.functions import TruncDate
        by_day = Notification.objects.filter(
            created_at__gte=seven_days_ago
        ).annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(
            count=Count('notification_id')
        ).order_by('day')
        
        data = {
            'total_notifications': total,
            'unread_notifications': unread,
            'urgent_notifications': urgent,
            'by_type': {item['notification_type']: item['count'] for item in by_type},
            'by_day': list(by_day)
        }
        
        serializer = NotificationStatsSerializer(data=data)
        serializer.is_valid()
        return Response(serializer.data)


class NotificationStatisticsView(APIView):
    """إحصائيات الإشعارات للمستخدم العادي"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # الإحصائيات
        total = Notification.objects.filter(user=user).count()
        unread = Notification.objects.filter(user=user, is_read=False).count()
        urgent = Notification.objects.filter(user=user, priority_level='urgent', is_read=False).count()
        
        # الإشعارات الحديثة (آخر 24 ساعة)
        today = Notification.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        # حسب النوع
        by_type = Notification.objects.filter(user=user).values(
            'notification_type'
        ).annotate(
            count=Count('notification_id')
        ).order_by('-count')[:5]
        
        return Response({
            'total': total,
            'unread': unread,
            'urgent_unread': urgent,
            'today': today,
            'by_type': list(by_type)
        })


class NotificationPreferencesView(APIView):
    """تفضيلات الإشعارات للمستخدم"""
    permission_classes = [IsAuthenticated]

    def get_preferences(self, user):
        """الحصول على التفضيلات أو إنشاء واحدة افتراضية"""
        prefs, created = NotificationPreference.objects.get_or_create(user=user)
        return prefs

    def get(self, request):
        prefs = self.get_preferences(request.user)
        serializer = NotificationPreferenceSerializer(prefs)
        return Response(serializer.data)

    def put(self, request):
        """تحديث تفضيلات الإشعارات"""
        prefs = self.get_preferences(request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': _('تم تحديث تفضيلات الإشعارات بنجاح'),
                'preferences': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)