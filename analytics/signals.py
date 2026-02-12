from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from reports.models import Report
from .models import DailyStats


@receiver(post_save, sender=Report)
def update_stats_on_report(sender, instance, created, **kwargs):
    """تحديث الإحصائيات عند إنشاء أو تحديث بلاغ"""
    try:
        from .services import AnalyticsService
        service = AnalyticsService()
        service.update_report_stats(instance, created)
    except Exception as e:
        # لا نعطل العملية الأساسية إذا فشل تحديث الإحصائيات
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to update analytics for report {instance.pk}: {str(e)}")
