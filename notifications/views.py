from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import Notification, NotificationPreference, PushNotificationToken
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationPreferenceSerializer, PushNotificationTokenSerializer,
    NotificationStatsSerializer, MarkAsReadSerializer
)
from .services import NotificationService


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet للإشعارات"""
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
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        user = request.user
        
        if data['read_all']:
            # تحديد كل الإشعارات كمقروءة
            notifications = Notification.objects.filter(
                user=user,
                is_read=False
            )
            count = notifications.count()
            notifications.update(is_read=True, read_at=timezone.now())
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
    def clear_all(self, request):
        """حذف كل الإشعارات المقروءة"""
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


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet لتفضيلات الإشعارات"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """تفضيلات المستخدم الحالي فقط"""
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        """الحصول على تفضيلات المستخدم الحالي"""
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
    
    def list(self, request, *args, **kwargs):
        """عرض تفضيلات المستخدم"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """تحديث التفضيلات (استخدام update بدلاً من create)"""
        return self.update(request, *args, **kwargs)


class PushNotificationTokenViewSet(viewsets.ModelViewSet):
    """ViewSet لرموز الإشعارات الدفعية"""
    serializer_class = PushNotificationTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """رموز المستخدم الحالي فقط"""
        return PushNotificationToken.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """إضافة المستخدم الحالي للبيانات"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """تعطيل رمز الجهاز"""
        token = self.get_object()
        token.is_active = False
        token.save()
        
        return Response({'message': 'تم تعطيل رمز الجهاز'})


class AdminNotificationViewSet(viewsets.ModelViewSet):
    """ViewSet للإشعارات (للمشرفين)"""
    serializer_class = NotificationCreateSerializer
    permission_classes = [IsAdminUser]
    queryset = Notification.objects.all().order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """إنشاء إشعارات جماعية"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
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
            count=Count('id')
        ).order_by('-count')
        
        # حسب اليوم (آخر 7 أيام)
        seven_days_ago = timezone.now() - timedelta(days=7)
        by_day = Notification.objects.filter(
            created_at__gte=seven_days_ago
        ).extra({
            'day': "DATE(created_at)"
        }).values('day').annotate(
            count=Count('id')
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
            count=Count('id')
        ).order_by('-count')[:5]
        
        return Response({
            'total': total,
            'unread': unread,
            'urgent_unread': urgent,
            'today': today,
            'by_type': list(by_type),
            'has_preferences': NotificationPreference.objects.filter(user=user).exists()
        })