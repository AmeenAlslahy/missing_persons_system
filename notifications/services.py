import json
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import logging
import threading

from .models import Notification
from accounts.models import User

logger = logging.getLogger(__name__)


class NotificationService:
    """خدمة إدارة الإشعارات (محسنة)"""
    
    def __init__(self):
        from django.conf import settings
        self.email_enabled = getattr(settings, 'EMAIL_ENABLED', False)
        self.sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        self.push_enabled = getattr(settings, 'PUSH_NOTIFICATIONS_ENABLED', False)
        self.site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        self._cache = {}  # تخزين مؤقت للتفضيلات
    
    def get_user_preferences(self, user):
        """الحصول على تفضيلات المستخدم مع التخزين المؤقت"""
        cache_key = f'user_prefs_{user.id}'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        from .models import NotificationPreference
        try:
            preferences, created = NotificationPreference.objects.get_or_create(user=user)
            self._cache[cache_key] = preferences
            return preferences
        except Exception as e:
            logger.error(f"خطأ في جلب تفضيلات المستخدم: {e}")
            return None
    
    def create_notification(self, user, notification_type, title, message, 
                           priority='normal', related_report=None, related_match=None,
                           action_required=False, action_url='', action_text='',
                           expiry_days=7, metadata=None, bypass_preferences=False):
        """
        إنشاء إشعار جديد (محسن)
        """
        try:
            preferences = None
            # التحقق من تفضيلات المستخدم (إذا لم يتم تجاوزها)
            if not bypass_preferences:
                preferences = self.get_user_preferences(user)
                if preferences and not preferences.should_notify(notification_type, priority):
                    logger.info(f"تم منع الإشعار حسب تفضيلات المستخدم {user.phone}")
                    return None
            
            # منع التكرار: التحقق من وجود إشعار مماثل لم يقرأ
            if self._check_duplicate(user, notification_type, title, priority):
                return None
            
            # حساب تاريخ الانتهاء
            expires_at = timezone.now() + timedelta(days=expiry_days) if expiry_days > 0 else None
            
            # إنشاء الإشعار
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                priority_level=priority,
                related_report=related_report,
                related_match=related_match,
                action_required=action_required,
                action_url=action_url,
                action_text=action_text or self._get_default_action_text(action_required),
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            # إرسال الإشعار حسب القنوات المتاحة
            self._deliver_notification(notification, preferences)
            
            return notification
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء إشعار: {e}")
            return None
    
    def _check_duplicate(self, user, notification_type, title, priority):
        """التحقق من وجود إشعار مكرر خلال نافذة زمنية قصيرة"""
        time_window = 5  # 5 دقائق
        if priority in ['urgent', 'high']:
            time_window = 1  # دقيقة واحدة فقط للإشعارات العاجلة
        
        cutoff = timezone.now() - timedelta(minutes=time_window)
        duplicate = Notification.objects.filter(
            user=user,
            notification_type=notification_type,
            title=title,
            is_read=False,
            created_at__gte=cutoff
        ).exists()
        
        if duplicate:
            logger.info(f"تم منع إشعار مكرر للمستخدم {user.phone}: {title}")
            return True
        
        return False
    
    def _get_default_action_text(self, action_required):
        """نص افتراضي للإجراء"""
        return _("عرض التفاصيل") if action_required else ""
    
    def _deliver_notification(self, notification, preferences=None):
        """
        توصيل الإشعار للمستخدم حسب القنوات المتاحة والتفضيلات
        """
        if not preferences:
            preferences = self.get_user_preferences(notification.user)
        
        delivery_methods = []
        
        # الإشعارات الدفعية
        if self.push_enabled and (not preferences or preferences.push_enabled):
            if self._send_push_notification(notification):
                delivery_methods.append('push')
        
        # البريد الإلكتروني
        if self.email_enabled and notification.user.email:
            if not preferences or preferences.email_enabled:
                if self._send_email_notification(notification):
                    delivery_methods.append('email')
        
        # الرسائل النصية
        if self.sms_enabled and notification.user.phone and notification.priority_level == 'urgent':
            if not preferences or preferences.sms_enabled:
                if self._send_sms_notification(notification):
                    delivery_methods.append('sms')
        
        if delivery_methods:
            logger.info(f"تم توصيل الإشعار {notification.notification_id} عبر: {', '.join(delivery_methods)}")
    
    def batch_create_notifications(self, notifications_data):
        """إنشاء مجموعة من الإشعارات دفعة واحدة"""
        created = []
        for data in notifications_data:
            notification = self.create_notification(**data)
            if notification:
                created.append(notification)
        return created
    
    def notify_admins(self, title, message, priority='normal', **kwargs):
        """إرسال إشعار لجميع المشرفين"""
        admins = User.objects.filter(is_staff=True, is_active=True)
        notifications = []
        
        for admin in admins:
            notification = self.create_notification(
                user=admin,
                notification_type='system_update',
                title=title,
                message=message,
                priority=priority,
                **kwargs
            )
            if notification:
                notifications.append(notification)
        
        return notifications
    
    def _send_push_notification(self, notification):
        """إرسال إشعار دفعي - للتنفيذ الفعلي لاحقاً"""
        logger.info(f"إرسال Push للإشعار {notification.notification_id}")
        return True

    def _send_email_notification(self, notification):
        """إرسال إشعار بالبريد الإلكتروني"""
        try:
            from django.core.mail import send_mail
            subject = f"{notification.title}"
            body = notification.message
            if notification.action_url:
                body += f"\n\nللمزيد من التفاصيل: {self.site_url}{notification.action_url}"
            
            # استخدام الخيوط لعدم تعطيل العملية الرئيسية
            threading.Thread(
                target=send_mail,
                kwargs={
                    'subject': subject,
                    'message': body,
                    'from_email': settings.DEFAULT_FROM_EMAIL,
                    'recipient_list': [notification.user.email],
                    'fail_silently': True
                }
            ).start()
            return True
        except:
            return False

    def _send_sms_notification(self, notification):
        """إرسال رسالة نصية - للتنفيذ الفعلي لاحقاً"""
        logger.info(f"إرسال SMS للإشعار {notification.notification_id} إلى {notification.user.phone}")
        return True

    def _send_email_notification_raw(self, email, subject, message):
        """إرسال بريد إلكتروني مباشر (للملخصات)"""
        try:
            from django.core.mail import send_mail
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
            return True
        except:
            return False

    def cleanup_expired_notifications(self):
        """تنظيف الإشعارات المنتهية"""
        now = timezone.now()
        expired = Notification.objects.filter(expires_at__lte=now)
        count = expired.count()
        expired.delete()
        return count

    # طرق للتوافق مع الإشارات (Signals)
    def notify_match_found(self, user, match):
        return self.create_notification(
            user=user,
            notification_type='match_found',
            title=_("تم العثور على مطابقة محتملة!"),
            message=_("تم العثور على تطابق بنسبة {}% مع بلاغك.").format(int(match.similarity_score * 100)),
            priority='high' if match.similarity_score > 0.8 else 'normal',
            related_match=match,
            action_required=True,
            action_url=f"/admin-dashboard/matches/?id={match.match_id}"
        )

    def notify_report_status_change(self, user, report, old_status, new_status):
        status_display = dict(report.STATUS_CHOICES).get(new_status, new_status)
        return self.create_notification(
            user=user,
            notification_type='report_status_change',
            title=_("تحديث حالة البلاغ"),
            message=_("تم تغيير حالة بلاغك عن {} إلى {}").format(
                str(report.person) if report.person else report.report_code, status_display),
            priority='normal',
            related_report=report,
            action_url=f"/admin-dashboard/reports/?id={report.report_id}"
        )

    def notify_verification_status(self, user, status):
        messages = {
            'verified': _("مبروك! تم التحقق من هويتك بنجاح."),
            'rejected': _("عذراً، تم رفض طلب التحقق من هويتك. يرجى مراجعة البيانات."),
            'pending': _("طلب التحقق من هويتك قيد المراجعة الآن.")
        }
        return self.create_notification(
            user=user,
            notification_type='verification_status',
            title=_("تحديث حالة التحقق"),
            message=messages.get(status, _("تم تحديث حالة التحقق الخاصة بك.")),
            priority='high' if status in ['verified', 'rejected'] else 'low'
        )