import json
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import logging

from .models import Notification, NotificationPreference, NotificationTemplate, PushNotificationToken
from accounts.models import User

logger = logging.getLogger(__name__)


class NotificationService:
    """خدمة إدارة الإشعارات"""
    
    def __init__(self):
        self.email_enabled = getattr(settings, 'EMAIL_ENABLED', False)
        self.sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        self.push_enabled = getattr(settings, 'PUSH_NOTIFICATIONS_ENABLED', False)
    
    def create_notification(self, user, notification_type, title, message, 
                           priority='normal', related_report=None, related_match=None,
                           action_required=False, action_url='', action_text='',
                           expiry_days=7, metadata=None):
        """
        إنشاء إشعار جديد
        """
        try:
            # الحصول على تفضيلات المستخدم
            preference, _ = NotificationPreference.objects.get_or_create(user=user)
            
            # التحقق إذا كان يمكن إرسال الإشعار
            if not preference.can_send_notification(notification_type, priority):
                logger.info(f"تم تجاوز إشعار للمستخدم {user.email} حسب التفضيلات")
                return None
            
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
                logger.info(f"تم منع إشعار مكرر للمستخدم {user.email}: {title}")
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
            
            # إرسال الإشعار حسب طريقة التوصيل المفضلة
            self._deliver_notification(notification, preference)
            
            return notification
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء إشعار: {e}")
            return None
    
    def create_notification_from_template(self, user, template_name, variables=None, 
                                         language=None, **kwargs):
        """
        إنشاء إشعار من قالب
        """
        try:
            template = NotificationTemplate.objects.get(
                template_name=template_name,
                is_active=True
            )
            
            # تحديد اللغة
            if not language:
                preference = NotificationPreference.objects.filter(user=user).first()
                language = preference.preferred_language if preference else 'ar'
            
            # توليد المحتوى من القالب
            content = template.render(language, variables or {})
            
            # إضافة المتغيرات الإضافية
            kwargs.update({
                'title': content['title'],
                'message': content['message'],
                'priority': content['priority'],
                'action_text': content.get('action_text'),
                'action_url': content.get('action_url'),
                'expiry_days': template.default_expiry_days,
            })
            
            # إنشاء الإشعار
            return self.create_notification(user, template.notification_type, **kwargs)
            
        except NotificationTemplate.DoesNotExist:
            logger.error(f"القالب غير موجود: {template_name}")
            return None
        except Exception as e:
            logger.error(f"خطأ في إنشاء إشعار من قالب: {e}")
            return None
    
    def notify_match_found(self, user, match_result):
        """
        إشعار المستخدم باكتشاف تطابق
        """
        try:
            title = _("تم العثور على تطابق محتمل")
            message = _(
                "تم العثور على تطابق محتمل بين بلاغك عن {missing_person} "
                "وشخص تم العثور عليه. درجة التشابه: {similarity}%"
            ).format(
                missing_person=match_result.missing_report.person_name,
                similarity=int(match_result.similarity_score * 100)
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
                    'confidence_score': match_result.confidence_score
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
            status_display = report.get_status_display()
            title = _("تغيير حالة البلاغ")
            message = _(
                "تم تغيير حالة بلاغك عن {person_name} من {old_status} إلى {new_status}."
            ).format(
                person_name=report.person_name,
                old_status=old_status,
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
                'verified': (_("تم التحقق من هويتك"), _("مبروك! تم التحقق من هويتك بنجاح.")),
                'rejected': (_("تم رفض طلب التحقق"), _("عذراً، لم يتم التحقق من هويتك. يرجى مراجعة البيانات المقدمة.")),
            }
            
            if status not in status_map:
                return None
            
            title, message = status_map[status]
            priority = 'high' if status == 'verified' else 'normal'
            
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
    
    def _deliver_notification(self, notification, preference):
        """
        توصيل الإشعار للمستخدم حسب التفضيلات
        """
        delivery_methods = []
        
        # الإشعارات الدفعية
        if self.push_enabled and preference.receive_push_notifications:
            if self._send_push_notification(notification):
                delivery_methods.append('push')
        
        # البريد الإلكتروني
        if self.email_enabled and preference.receive_email_notifications:
            if self._send_email_notification(notification):
                delivery_methods.append('email')
        
        # الرسائل النصية (SMS)
        if self.sms_enabled and preference.receive_sms_notifications and notification.priority_level == 'urgent':
            if self._send_sms_notification(notification):
                delivery_methods.append('sms')
        
        # تحديث حالة الإرسال
        if delivery_methods:
            notification.mark_as_sent(delivery_methods)
    
    def _send_push_notification(self, notification):
        """
        إرسال إشعار دفعي (يمكن دمج مع Firebase Cloud Messaging أو OneSignal)
        """
        try:
            # الحصول على رموز الأجهزة النشطة للمستخدم
            tokens = PushNotificationToken.objects.filter(
                user=notification.user,
                is_active=True
            )
            
            if not tokens:
                return False
            
            # هنا يمكن إضافة منطق إرسال الإشعارات الدفعية
            # مثال: Firebase Cloud Messaging, OneSignal, إلخ.
            
            # حالياً نرجع True للمحاكاة
            return True
            
        except Exception as e:
            logger.error(f"خطأ في الإشعار الدفعي: {e}")
            return False
    
    def _send_email_notification(self, notification):
        """
        إرسال إشعار بالبريد الإلكتروني
        """
        try:
            if not notification.user.email:
                return False
            
            subject = f"{notification.title} - نظام البحث عن المفقودين"
            
            # بناء محتوى البريد
            body = f"""
            {notification.message}
            
            """
            
            if notification.action_url:
                body += f"""
                رابط الإجراء: {notification.action_url}
                """
            
            body += f"""
            ---
            نظام البحث عن المفقودين
            {settings.SITE_URL}
            """
            
            # إرسال البريد
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.user.email],
                fail_silently=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في البريد الإلكتروني: {e}")
            return False
    
    def _send_sms_notification(self, notification):
        """
        إرسال إشعار برسالة نصية (SMS)
        """
        # هنا يمكن إضافة منطق إرسال الرسائل النصية
        # مثال: Twilio, Unifonic, إلخ.
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