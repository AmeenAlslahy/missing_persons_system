from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

from .models import Notification
from matching.models import MatchResult

logger = logging.getLogger(__name__)

# تأجيل استيراد الخدمة لتجنب التبعية الدائرية
def get_notification_service():
    from .services import NotificationService
    return NotificationService()


@receiver(post_save, sender=Notification)
def trigger_websocket_notification(sender, instance, created, **kwargs):
    """إرسال الإشعار فوراً عبر WebSocket عند الإنشاء"""
    if created:
        try:
            channel_layer = get_channel_layer()
            group_name = f"user_{instance.user.id}_notifications"
            
            from .serializers import NotificationSerializer
            serializer = NotificationSerializer(instance)
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'send_notification',
                    'notification': serializer.data
                }
            )
            logger.info(f"WebSocket trigger sent for notification {instance.notification_id}")
        except Exception as e:
            logger.error(f"Error triggering WebSocket: {e}")


@receiver(post_save, sender=MatchResult)
def notify_match_found(sender, instance, created, **kwargs):
    """إشعار المستخدمين عند اكتشاف تطابق (مفعل)"""
    if created and instance.match_status == 'pending':
        service = get_notification_service()
        
        # إشعار مالك بلاغ المفقود
        if instance.report_1 and instance.report_1.user:
            service.notify_match_found(instance.report_1.user, instance)
        
        # إشعار مالك بلاغ المعثور عليه
        if instance.report_2 and instance.report_2.user:
            service.notify_match_found(instance.report_2.user, instance)


@receiver(post_save, sender='reports.Report')
def notify_report_status_change(sender, instance, created, **kwargs):
    """إشعار المستخدم بتغيير حالة البلاغ (محسن)"""
    if created:
        return
    
    # التحقق من حقل الحالة إذا كان متاحاً في update_fields
    if kwargs.get('update_fields') and 'status' not in kwargs['update_fields']:
        return
    
    def send_notification():
        try:
            # يمكن جلب الحالة القديمة من الكاش أو قاعدة البيانات إذا لزم الأمر
            old_status = "unknown" 
            new_status = instance.status
            
            service = get_notification_service()
            service.notify_report_status_change(
                instance.user,
                instance,
                old_status,
                new_status
            )
        except Exception as e:
            logger.warning(f"Failed to send notification for report {instance.pk}: {str(e)}")
    
    transaction.on_commit(send_notification)


@receiver(post_save, sender='accounts.User')
def notify_verification_status(sender, instance, created, **kwargs):
    """إشعار المستخدم بتغيير حالة التحقق"""
    if created:
        return
    
    if kwargs.get('update_fields') and 'verification_status' not in kwargs['update_fields']:
        return
    
    def send_notification():
        try:
            service = get_notification_service()
            service.notify_verification_status(instance, instance.verification_status)
        except Exception as e:
            logger.warning(f"Failed to send verification notification for user {instance.pk}: {str(e)}")
    
    transaction.on_commit(send_notification)