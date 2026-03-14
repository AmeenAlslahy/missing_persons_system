from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import User
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    """إجراءات قبل حفظ المستخدم"""
    # تنظيف رقم الهاتف
    if instance.phone:
        instance.phone = instance.phone.strip()
    
    # تنظيف الأسماء
    if instance.first_name:
        instance.first_name = instance.first_name.strip()
    if instance.middle_name:
        instance.middle_name = instance.middle_name.strip()
    if instance.last_name:
        instance.last_name = instance.last_name.strip()


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """إجراءات ما بعد حفظ المستخدم"""
    if created:
        logger.info(f"New user created: {instance.phone}")
    else:
        logger.info(f"User updated: {instance.phone}")