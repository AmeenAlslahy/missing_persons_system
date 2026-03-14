from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .services import NotificationService
from .models import Notification, NotificationPreference
from accounts.models import User

logger = logging.getLogger(__name__)

@shared_task
def cleanup_expired_notifications():
    """تنظيف الإشعارات منتهية الصلاحية دورياً"""
    service = NotificationService()
    count = service.cleanup_expired_notifications()
    logger.info(f"Task: Deleted {count} expired notifications")
    return count

@shared_task
def send_daily_digests():
    """إرسال ملخص يومي للإشعارات غير المقروءة"""
    users = User.objects.filter(is_active=True)
    sent_count = 0
    service = NotificationService()
    
    for user in users:
        # التحقق مما إذا كان لدى المستخدم إشعارات غير مقروءة من الـ 24 ساعة الماضية
        yesterday = timezone.now() - timedelta(days=1)
        unread = Notification.objects.filter(
            user=user, 
            is_read=False, 
            created_at__gte=yesterday
        ).count()
        
        if unread > 0 and user.email:
            # التحقق من التفضيلات (يمكن إضافة خيار للملخص اليومي في NotificationPreference)
            subject = f"لديك {unread} إشعارات غير مقروءة في نظام المفقودين"
            message = f"مرحباً {user.phone or user.email}،\n\nلديك {unread} إشعارات جديدة بانتظارك في النظام.\nيرجى زيارة الموقع للمراجعة."
            
            if service._send_email_notification_raw(user.email, subject, message):
                sent_count += 1
                
    return sent_count

@shared_task
def send_weekly_report_to_admins():
    """إرسال تقرير أداء أسبوعي للمشرفين"""
    from django.db.models import Count
    last_week = timezone.now() - timedelta(days=7)
    
    # إحصائيات الأسبوع
    total_new = Notification.objects.filter(created_at__gte=last_week).count()
    matches = Notification.objects.filter(
        notification_type='match_found', 
        created_at__gte=last_week
    ).count()
    
    admins = User.objects.filter(is_staff=True, is_active=True)
    service = NotificationService()
    
    subject = "التقرير الأسبوعي لنظام الإشعارات"
    message = f"""
    إحصائيات الإشعارات للأسبوع الماضي:
    - إجمالي الإشعارات الجديدة: {total_new}
    - تنبيهات المطابقة المكتشفة: {matches}
    - البلاغات المحدثة: {Notification.objects.filter(notification_type='report_status_change', created_at__gte=last_week).count()}
    """
    
    for admin in admins:
        if admin.email:
            service._send_email_notification_raw(admin.email, subject, message)
            
    return admins.count()
