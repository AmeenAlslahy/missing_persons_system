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
    """خدمة إدارة الإشعارات"""
    
    def __init__(self):
        self.email_enabled = getattr(settings, 'EMAIL_ENABLED', False)
        self.sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        self.push_enabled = getattr(settings, 'PUSH_NOTIFICATIONS_ENABLED', False)
        self.site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    
    def create_notification(self, user, notification_type, title, message, 
                           priority='normal', related_report=None, related_match=None,
                           action_required=False, action_url='', action_text='',
                           expiry_days=7, metadata=None):
        """
        إنشاء إشعار جديد
        """
        try:
            # منع التكرار: التحقق من وجود إشعار مماثل لم يقرأ خلال آخر 5 دقائق
            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            duplicate = Notification.objects.filter(
                user=user,
                notification_type=notification_type,
                title=title,
                is_read=False,
                created_at__gte=five_minutes_ago
            ).exists()
            
            if duplicate:
                logger.info(f"تم منع إشعار مكرر للمستخدم {user.phone}: {title}")
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
                action_text=action_text,
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            # إرسال الإشعار حسب القنوات المتاحة
            self._deliver_notification(notification)
            
            return notification
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء إشعار: {e}")
            return None
    
    def notify_match_found(self, user, match_result):
        """
        إشعار المستخدم باكتشاف تطابق
        """
        try:
            # تحديد البلاغ المناسب للمستخدم
            report = None
            if match_result.report_1.user == user:
                report = match_result.report_1
                other_report = match_result.report_2
            else:
                report = match_result.report_2
                other_report = match_result.report_1
            
            if not report:
                return None
            
            title = _("تم العثور على تطابق محتمل")
            message = _(
                "تم العثور على تطابق محتمل بين بلاغك عن {person_name} "
                "وشخص آخر. نسبة التشابه: {similarity}%"
            ).format(
                person_name=str(report.person) if report.person else _("غير معروف"),
                similarity=int(match_result.similarity_score * 100) if match_result.similarity_score else 0
            )
            
            action_url = f"/admin-dashboard/matches/?id={match_result.match_id}"
            action_text = _("عرض التفاصيل")
            
            return self.create_notification(
                user=user,
                notification_type='match_found',
                title=title,
                message=message,
                priority='high',
                related_match=match_result,
                action_required=True,
                action_url=action_url,
                action_text=action_text,
                metadata={
                    'match_id': str(match_result.match_id),
                    'similarity_score': match_result.similarity_score,
                    'report_id': str(report.report_id),
                    'other_report_id': str(other_report.report_id) if other_report else None
                }
            )
            
        except Exception as e:
            logger.error(f"خطأ في إشعار اكتشاف تطابق: {e}")
            return None
    
    def notify_report_status_change(self, user, report, old_status, new_status):
        """
        إشعار المستخدم بتغيير حالة بلاغه
        """
        try:
            status_display = dict(report.STATUS_CHOICES).get(new_status, new_status)
            old_status_display = dict(report.STATUS_CHOICES).get(old_status, old_status)
            
            title = _("تغيير حالة البلاغ")
            message = _(
                "تم تغيير حالة بلاغك عن {person_name} من {old_status} إلى {new_status}."
            ).format(
                person_name=str(report.person) if report.person else _("غير معروف"),
                old_status=old_status_display,
                new_status=status_display
            )
            
            action_url = f"/admin-dashboard/reports/?id={report.report_id}"
            action_text = _("عرض البلاغ")
            
            return self.create_notification(
                user=user,
                notification_type='report_status_change',
                title=title,
                message=message,
                priority='normal',
                related_report=report,
                action_required=True,
                action_url=action_url,
                action_text=action_text,
                metadata={
                    'report_id': str(report.report_id),
                    'old_status': old_status,
                    'new_status': new_status
                }
            )
            
        except Exception as e:
            logger.error(f"خطأ في إشعار تغيير حالة البلاغ: {e}")
            return None
    
    def notify_verification_status(self, user, status):
        """
        إشعار المستخدم بحالة التحقق
        """
        try:
            status_map = {
                'verified': (_("تم التحقق من هويتك"), _("مبروك! تم التحقق من هويتك بنجاح."), 'high'),
                'rejected': (_("تم رفض طلب التحقق"), _("عذراً، لم يتم التحقق من هويتك. يرجى مراجعة البيانات المقدمة."), 'normal'),
                'pending': (_("طلب التحقق قيد المراجعة"), _("طلب التحقق الخاص بك قيد المراجعة من قبل المشرفين."), 'normal'),
            }
            
            if status not in status_map:
                return None
            
            title, message, priority = status_map[status]
            
            return self.create_notification(
                user=user,
                notification_type='verification_status',
                title=title,
                message=message,
                priority=priority,
                metadata={'verification_status': status}
            )
            
        except Exception as e:
            logger.error(f"خطأ في إشعار حالة التحقق: {e}")
            return None
    
    def send_bulk_notification(self, notification_type, title, message, 
                              user_ids=None, priority='normal', **kwargs):
        """
        إرسال إشعار جماعي
        """
        try:
            if user_ids:
                users = User.objects.filter(id__in=user_ids, is_active=True)
            else:
                # إرسال لجميع المستخدمين النشطين
                users = User.objects.filter(is_active=True)
            
            notifications = []
            for user in users:
                notification = self.create_notification(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    priority=priority,
                    **kwargs
                )
                if notification:
                    notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            logger.error(f"خطأ في الإشعار الجماعي: {e}")
            return []
    
    def _deliver_notification(self, notification):
        """
        توصيل الإشعار للمستخدم حسب القنوات المتاحة
        """
        delivery_methods = []
        
        # الإشعارات الدفعية (إذا كانت مفعلة)
        if self.push_enabled:
            if self._send_push_notification(notification):
                delivery_methods.append('push')
        
        # البريد الإلكتروني (للمستخدمين الذين لديهم بريد)
        if self.email_enabled and notification.user.email:
            if self._send_email_notification(notification):
                delivery_methods.append('email')
        
        # الرسائل النصية (للإشعارات العاجلة فقط)
        if self.sms_enabled and notification.priority_level == 'urgent' and notification.user.phone:
            if self._send_sms_notification(notification):
                delivery_methods.append('sms')
    
    def _send_push_notification(self, notification):
        """
        إرسال إشعار دفعي - للتنفيذ لاحقاً
        """
        # TODO: تنفيذ Firebase Cloud Messaging أو OneSignal
        return False
    
    def _send_email_notification(self, notification):
        """
        إرسال إشعار بالبريد الإلكتروني (بشكل غير متزامن)
        """
        try:
            subject = f"{notification.title} - نظام البحث عن المفقودين"
            
            body = f"""
            {notification.message}
            
            """
            
            if notification.action_url:
                body += f"\n{notification.action_text or 'رابط الإجراء'}: {self.site_url}{notification.action_url}\n"
            
            body += f"\n---\nنظام البحث عن المفقودين\n{self.site_url}\n"
            
            # إرسال البريد في خيط منفصل
            email_thread = threading.Thread(
                target=send_mail,
                kwargs={
                    'subject': subject,
                    'message': body,
                    'from_email': settings.DEFAULT_FROM_EMAIL,
                    'recipient_list': [notification.user.email],
                    'fail_silently': True
                }
            )
            email_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في البريد الإلكتروني: {e}")
            return False
    
    def _send_sms_notification(self, notification):
        """
        إرسال إشعار برسالة نصية - للتنفيذ لاحقاً
        """
        # TODO: تنفيذ Twilio, Unifonic, إلخ.
        return False
    
    def cleanup_expired_notifications(self):
        """
        تنظيف الإشعارات المنتهية الصلاحية
        """
        try:
            expired = Notification.objects.filter(
                expires_at__lt=timezone.now(),
                is_read=True
            )
            
            count = expired.count()
            expired.delete()
            
            logger.info(f"تم حذف {count} إشعار منتهي الصلاحية")
            return count
            
        except Exception as e:
            logger.error(f"خطأ في تنظيف الإشعارات: {e}")
            return 0