from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

# تأجيل استيراد الخدمة لتجنب التبعية الدائرية
def get_notification_service():
    from .services import NotificationService
    return NotificationService()


# تعليق signal المطابقة مؤقتاً حتى يكتمل تطبيق matching
# @receiver(post_save, sender=MatchResult)
# def notify_match_found(sender, instance, created, **kwargs):
#     """إشعار المستخدمين عند اكتشاف تطابق"""
#     if created and instance.match_status == 'pending':
#         service = get_notification_service()
#         
#         # إشعار مالك بلاغ المفقود
#         if instance.missing_report and instance.missing_report.user:
#             service.notify_match_found(instance.missing_report.user, instance)
#         
#         # إشعار مالك بلاغ المعثور عليه
#         if instance.found_report and instance.found_report.user:
#             service.notify_match_found(instance.found_report.user, instance)


@receiver(post_save, sender='reports.Report')
def notify_report_status_change(sender, instance, created, **kwargs):
    """إشعار المستخدم بتغيير حالة البلاغ"""
    # نتجنب الإشعار عند الإنشاء
    if created:
        return
    
    # نتحقق إذا كان التغيير في حقل status
    if kwargs.get('update_fields') and 'status' not in kwargs['update_fields']:
        return
    
    # نستخدم transaction.on_commit لضمان حفظ التغيير قبل الإشعار
    def send_notification():
        try:
            # الحصول على الحالة القديمة - هذا يحتاج تحسين
            # حالياً نستخدم طريقة مبسطة
            old_status = 'pending'  # قيمة افتراضية
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