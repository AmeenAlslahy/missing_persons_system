from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_logged_out
from .services import AuditService
import logging

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """تسجيل دخول المستخدم"""
    AuditService.log_login(user, request, success=True)


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """تسجيل خروج المستخدم"""
    if user:
        AuditService.log_logout(user, request)


def audit_model_save(sender, instance, created, **kwargs):
    """تسجيل إضافة أو تعديل نموذج"""
    try:
        if not hasattr(instance, 'skip_audit'):
            model_name = sender.__name__
            action = 'CREATE' if created else 'UPDATE'
            
            # يمكن إضافة منطق لتسجيل التغييرات
            logger.debug(f"Audit: {action} on {model_name}")
    except Exception as e:
        logger.error(f"Error in audit_model_save: {e}")


def audit_model_delete(sender, instance, **kwargs):
    """تسجيل حذف نموذج"""
    try:
        if not hasattr(instance, 'skip_audit'):
            model_name = sender.__name__
            logger.debug(f"Audit: DELETE on {model_name}")
    except Exception as e:
        logger.error(f"Error in audit_model_delete: {e}")


# يمكن تفعيل هذه الإشارات عند الحاجة
# post_save.connect(audit_model_save)
# pre_delete.connect(audit_model_delete)