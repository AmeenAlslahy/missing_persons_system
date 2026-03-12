from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Report, ReportImage
import logging

logger = logging.getLogger(__name__)

# تم إزالة الإشارة الخاصة بـ primary_photo لأن الحقل غير موجود
# يمكن إضافة إشارات أخرى هنا عند الحاجة

@receiver(post_save, sender=ReportImage)
def log_image_upload(sender, instance, created, **kwargs):
    """تسجيل رفع الصور"""
    if created:
        logger.info(f"Image uploaded for report {instance.report.report_code}")