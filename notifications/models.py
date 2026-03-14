from django.db import models
from accounts.models import User
from reports.models import Report
from matching.models import MatchResult
import uuid
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('match_found', _('تم العثور على تطابق')),
        ('report_status_change', _('تغيير حالة البلاغ')),
        ('verification_status', _('تغيير حالة التحقق')),
        ('urgent_alert', _('تنبيه عاجل')),
        ('system_update', _('تحديث النظام')),
        ('message_from_admin', _('رسالة من المشرف')),
    ]
    
    PRIORITY_LEVELS = [
        ('low', _('منخفضة')),
        ('normal', _('عادية')),
        ('high', _('عالية')),
        ('urgent', _('عاجلة')),
    ]
    
    notification_id = models.UUIDField(_('معرف الإشعار'), default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name=_('المستهدف'))
    
    notification_type = models.CharField(_('نوع الإشعار'), max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(_('العنوان'), max_length=255)
    message = models.TextField(_('المحتوى'))
    priority_level = models.CharField(_('مستوى الأولوية'), max_length=20, choices=PRIORITY_LEVELS, default='normal')
    
    is_read = models.BooleanField(_('تمت القراءة'), default=False)
    read_at = models.DateTimeField(_('وقت القراءة'), null=True, blank=True)
    
    # للإشعارات التي تتطلب إجراء
    action_required = models.BooleanField(_('يتطلب إجراء'), default=False)
    action_url = models.CharField(_('رابط الإجراء'), max_length=500, blank=True)
    action_text = models.CharField(_('نص الزر'), max_length=100, blank=True)
    
    # الروابط مع التطبيقات الأخرى
    related_report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    related_match = models.ForeignKey('matching.MatchResult', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    # بيانات إضافية
    metadata = models.JSONField(_('بيانات إضافية'), default=dict, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    expires_at = models.DateTimeField(_('تاريخ الانتهاء'), null=True, blank=True)

    class Meta:
        verbose_name = _('إشعار')
        verbose_name_plural = _('الإشعارات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.phone}"

    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """تفضيلات المستخدم للإشعارات"""
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='notification_preferences', verbose_name=_('المستخدم'))
    
    # قنوات الاتصال
    email_enabled = models.BooleanField(_('البريد الإلكتروني'), default=True)
    sms_enabled = models.BooleanField(_('الرسائل النصية'), default=False)
    push_enabled = models.BooleanField(_('الإشعارات الدفعية'), default=True)
    
    # إعدادات حسب النوع
    notify_match_found = models.BooleanField(_('اكتشاف تطابق'), default=True)
    notify_report_status = models.BooleanField(_('تغيير حالة البلاغ'), default=True)
    notify_verification = models.BooleanField(_('حالة التحقق'), default=True)
    notify_system = models.BooleanField(_('تحديثات النظام'), default=True)
    notify_admin = models.BooleanField(_('رسائل المشرفين'), default=True)
    
    # إعدادات الأولوية الدنيا لإشعارات البريد/SMS
    min_priority = models.CharField(
        _('الحد الأدنى للأولوية'), 
        max_length=20, 
        choices=Notification.PRIORITY_LEVELS,
        default='normal'
    )
    
    # أوقات عدم الإزعاج
    quiet_hours_start = models.TimeField(_('بدء وقت الهدوء'), null=True, blank=True)
    quiet_hours_end = models.TimeField(_('نهاية وقت الهدوء'), null=True, blank=True)
    
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تفضيلات الإشعارات')
        verbose_name_plural = _('تفضيلات الإشعارات')
    
    def __str__(self):
        return f"تفضيلات {self.user}"
    
    def is_quiet_hours(self):
        """التحقق مما إذا كان الوقت الحالي ضمن ساعات الهدوء"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        from django.utils import timezone
        now = timezone.now().time()
        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # عبر منتصف الليل
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
    
    def should_notify(self, notification_type, priority):
        """التحقق مما إذا كان يجب إرسال الإشعار"""
        # التحقق من الأولوية
        priority_levels = ['low', 'normal', 'high', 'urgent']
        try:
            min_priority_index = priority_levels.index(self.min_priority)
            current_priority_index = priority_levels.index(priority)
        except ValueError:
            return True
            
        if current_priority_index < min_priority_index:
            return False
        
        # التحقق من ساعات الهدوء (للإشعارات غير العاجلة)
        if priority not in ['urgent', 'high'] and self.is_quiet_hours():
            return False
        
        # التحقق من نوع الإشعار
        type_map = {
            'match_found': self.notify_match_found,
            'report_status_change': self.notify_report_status,
            'verification_status': self.notify_verification,
            'system_update': self.notify_system,
            'message_from_admin': self.notify_admin,
        }
        
        return type_map.get(notification_type, True)