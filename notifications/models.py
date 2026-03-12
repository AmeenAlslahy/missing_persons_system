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