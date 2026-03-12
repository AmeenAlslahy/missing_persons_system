from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
import logging

from reports.models import Report
from matching.models import MatchResult
from accounts.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Report)
def update_stats_on_report_save(sender, instance, created, **kwargs):
    """تحديث الإحصائيات عند إنشاء أو تحديث بلاغ"""
    try:
        from .services import AnalyticsService
        
        def update_stats():
            service = AnalyticsService()
            service.update_report_stats(instance, created)
            logger.info(f"Updated analytics for report {instance.report_code}")
        
        # تنفيذ بعد commit لضمان حفظ البيانات
        transaction.on_commit(update_stats)
        
    except Exception as e:
        logger.error(f"Failed to update analytics for report {instance.pk}: {str(e)}")


@receiver(post_delete, sender=Report)
def update_stats_on_report_delete(sender, instance, **kwargs):
    """تحديث الإحصائيات عند حذف بلاغ"""
    try:
        from .services import AnalyticsService
        
        def update_stats():
            service = AnalyticsService()
            service.update_daily_stats()
            logger.info(f"Updated analytics after report deletion")
        
        transaction.on_commit(update_stats)
        
    except Exception as e:
        logger.error(f"Failed to update analytics after report deletion: {str(e)}")


@receiver(post_save, sender=MatchResult)
def update_stats_on_match_save(sender, instance, created, **kwargs):
    """تحديث الإحصائيات عند إنشاء أو تحديث مطابقة"""
    try:
        from .services import AnalyticsService
        
        def update_stats():
            service = AnalyticsService()
            service.update_daily_stats()
            service.update_performance_metrics()
            logger.info(f"Updated analytics for match {instance.match_id}")
        
        transaction.on_commit(update_stats)
        
    except Exception as e:
        logger.error(f"Failed to update analytics for match {instance.pk}: {str(e)}")


@receiver(post_save, sender=User)
def update_stats_on_user_save(sender, instance, created, **kwargs):
    """تحديث الإحصائيات عند إنشاء مستخدم جديد"""
    try:
        if created:
            from .services import AnalyticsService
            
            def update_stats():
                service = AnalyticsService()
                service.update_daily_stats()
                logger.info(f"Updated analytics for new user {instance.phone}")
            
            transaction.on_commit(update_stats)
        
    except Exception as e:
        logger.error(f"Failed to update analytics for user {instance.pk}: {str(e)}")