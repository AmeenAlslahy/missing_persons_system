from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from accounts.models import User
from reports.models import Report
from matching.models import MatchResult
from .models import NotificationPreference
from .services import NotificationService


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """إنشاء تفضيلات إشعارات عند إنشاء مستخدم جديد"""
    if created:
        NotificationPreference.objects.create(user=instance)


@receiver(post_save, sender=MatchResult)
def notify_match_found(sender, instance, created, **kwargs):
    """إشعار المستخدمين عند اكتشاف تطابق"""
    if created and instance.match_status == 'pending':
        service = NotificationService()
        
        # إشعار مالك بلاغ المفقود
        service.notify_match_found(instance.missing_report.user, instance)
        
        # إشعار مالك بلاغ المعثور عليه
        service.notify_match_found(instance.found_report.user, instance)


@receiver(post_save, sender=Report)
def notify_report_status_change(sender, instance, **kwargs):
    """إشعار المستخدم بتغيير حالة البلاغ"""
    if kwargs.get('update_fields') is not None and 'status' in kwargs['update_fields']:
        # الحصول على الحالة القديمة (قد يحتاج تخزين في cache)
        # حالياً نستخدم بسيط
        try:
            service = NotificationService()
            service.notify_report_status_change(
                instance.user,
                instance,
                'unknown',  # يمكن تعديل هذا
                instance.status
            )
        except Exception as e:
            # لا نعطل العملية الأساسية إذا فشل الإشعار
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send notification for report {instance.pk}: {str(e)}")


@receiver(post_save, sender=User)
def notify_verification_status(sender, instance, **kwargs):
    """إشعار المستخدم بتغيير حالة التحقق"""
    if kwargs.get('update_fields') is not None and 'verification_status' in kwargs['update_fields']:
        service = NotificationService()
        service.notify_verification_status(instance, instance.verification_status)