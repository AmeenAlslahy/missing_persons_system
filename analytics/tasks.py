# analytics/tasks.py
"""
المهام المجدولة لتطبيق analytics
يتطلب تثبيت celery
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .services import AnalyticsService
from .models import DailyStats, AnalyticsReport

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_analytics_data():
    """تنظيف البيانات التحليلية القديمة (كل أسبوع)"""
    service = AnalyticsService()
    result = service.cleanup_old_data(days_to_keep=90)
    
    if result:
        logger.info(f"✅ تم التنظيف: {result}")
    else:
        logger.error("❌ فشل تنظيف البيانات القديمة")
    
    return result


@shared_task
def update_all_stats():
    """تحديث جميع الإحصائيات (كل ساعة)"""
    service = AnalyticsService()
    result = service.update_all_stats()
    
    logger.info("✅ تم تحديث جميع الإحصائيات")
    return True


@shared_task
def update_daily_stats():
    """تحديث الإحصائيات اليومية (كل يوم في منتصف الليل)"""
    service = AnalyticsService()
    result = service.update_daily_stats()
    
    if result:
        logger.info(f"✅ تم تحديث إحصائيات اليوم: {result.date}")
    else:
        logger.error("❌ فشل تحديث إحصائيات اليوم")
    
    return result.date if result else None


@shared_task
def generate_scheduled_reports():
    """توليد التقارير المجدولة (كل يوم)"""
    today = timezone.now().date()
    
    # الحصول على التقارير المجدولة التي يحين موعدها
    reports = AnalyticsReport.objects.filter(
        is_scheduled=True,
        next_run__date=today,
        status__in=['draft', 'ready']
    )
    
    generated_count = 0
    for report in reports:
        success = report.generate_report()
        if success:
            generated_count += 1
            logger.info(f"✅ تم توليد التقرير: {report.report_name}")
    
    logger.info(f"✅ تم توليد {generated_count} تقرير مجدول")
    return generated_count


@shared_task
def warm_cache():
    """تسخين الكاش للبيانات المهمة (كل ساعة)"""
    service = AnalyticsService()
    
    # تسخين كاش dashboard
    dashboard_stats = service.get_dashboard_stats()
    
    # تسخين كاش matching stats
    matching_stats = service.get_matching_stats()
    
    logger.info("✅ تم تسخين الكاش")
    
    return {
        'dashboard_stats': bool(dashboard_stats),
        'matching_stats': bool(matching_stats)
    }