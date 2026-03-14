from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Report, ReportImage
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReportImage)
def log_image_upload(sender, instance, created, **kwargs):
    """تسجيل رفع الصور"""
    if created:
        logger.info(f"Image uploaded for report {instance.report.report_code}")


@receiver(pre_delete, sender=ReportImage)
def cleanup_image_files(sender, instance, **kwargs):
    """حذف ملف الصورة من التخزين عند حذف السجل"""
    if instance.image_path:
        try:
            storage = instance.image_path.storage
            if storage.exists(instance.image_path.name):
                storage.delete(instance.image_path.name)
                logger.info(f"Deleted image file: {instance.image_path.name}")
        except Exception as e:
            logger.error(f"Error deleting image file: {e}")