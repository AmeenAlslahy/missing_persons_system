from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from reports.models import Report
from matching.models import MatchResult
import uuid


class Notification(models.Model):
    """نموذج الإشعارات"""
    
    # أنواع الإشعارات
    class NotificationType(models.TextChoices):
        MATCH_FOUND = 'match_found', _('تم العثور على تطابق')
        REPORT_STATUS_CHANGE = 'report_status_change', _('تغيير حالة البلاغ')
        REPORT_REVIEWED = 'report_reviewed', _('تمت مراجعة البلاغ')
        MESSAGE_FROM_ADMIN = 'message_from_admin', _('رسالة من المشرف')
        VERIFICATION_STATUS = 'verification_status', _('حالة التحقق')
        SYSTEM_UPDATE = 'system_update', _('تحديث النظام')
        VOLUNTEER_ASSIGNMENT = 'volunteer_assignment', _('مهمة تطوعية')
        URGENT_ALERT = 'urgent_alert', _('تنبيه عاجل')
    
    # مستوى الأولوية
    class PriorityLevel(models.TextChoices):
        URGENT = 'urgent', _('عاجل')
        HIGH = 'high', _('مهم')
        NORMAL = 'normal', _('عادي')
        LOW = 'low', _('منخفض')
    
    notification_id = models.UUIDField(_('معرف الإشعار'), default=uuid.uuid4, editable=False, unique=True)
    
    # المستخدم المستهدف
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name=_('المستخدم'))
    
    # معلومات الإشعار
    notification_type = models.CharField(
        _('نوع الإشعار'), 
        max_length=50, 
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM_UPDATE
    )
    title = models.CharField(_('عنوان الإشعار'), max_length=255)
    message = models.TextField(_('نص الإشعار'))
    
    # الأولوية
    priority_level = models.CharField(
        _('مستوى الأولوية'), 
        max_length=20, 
        choices=PriorityLevel.choices,
        default=PriorityLevel.NORMAL
    )
    
    # الارتباطات (اختيارية)
    related_report = models.ForeignKey(
        Report, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='notifications',
        verbose_name=_('البلاغ المرتبط')
    )
    related_match = models.ForeignKey(
        MatchResult, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='notifications',
        verbose_name=_('المطابقة المرتبطة')
    )
    
    # الإجراءات
    action_required = models.BooleanField(_('يتطلب إجراء'), default=False)
    action_url = models.URLField(_('رابط الإجراء'), blank=True)
    action_text = models.CharField(_('نص الإجراء'), max_length=100, blank=True)
    
    # الحالة
    is_read = models.BooleanField(_('تمت القراءة'), default=False)
    is_sent = models.BooleanField(_('تم الإرسال'), default=False)
    delivery_method = models.JSONField(
        _('طريقة التوصيل'),
        default=list,
        help_text='قائمة بطرق التوصيل المستخدمة: [push, email, sms, in_app]'
    )
    
    # التواريخ
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    sent_at = models.DateTimeField(_('تاريخ الإرسال'), null=True, blank=True)
    read_at = models.DateTimeField(_('تاريخ القراءة'), null=True, blank=True)
    expires_at = models.DateTimeField(_('تاريخ الانتهاء'), null=True, blank=True)
    
    # بيانات إضافية
    metadata = models.JSONField(_('بيانات إضافية'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('إشعار')
        verbose_name_plural = _('الإشعارات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['priority_level', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_sent(self, delivery_methods=None):
        """تحديد الإشعار كمرسل"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = timezone.now()
            
            if delivery_methods:
                self.delivery_method = delivery_methods
            
            self.save()
    
    def should_expire(self):
        """التحقق إذا كان الإشعار منتهي الصلاحية"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_action_data(self):
        """الحصول على بيانات الإجراء"""
        if self.action_required and self.action_url:
            return {
                'url': self.action_url,
                'text': self.action_text or 'اتخاذ إجراء',
                'type': self.notification_type
            }
        return None


class NotificationPreference(models.Model):
    """تفضيلات الإشعارات للمستخدم"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # تفعيل/تعطيل أنواع الإشعارات
    enable_match_notifications = models.BooleanField(_('إشعارات التطابق'), default=True)
    enable_report_updates = models.BooleanField(_('تحديثات البلاغات'), default=True)
    enable_admin_messages = models.BooleanField(_('رسائل المشرفين'), default=True)
    enable_system_updates = models.BooleanField(_('تحديثات النظام'), default=True)
    enable_urgent_alerts = models.BooleanField(_('تنبيهات عاجلة'), default=True)
    enable_volunteer_alerts = models.BooleanField(_('تنبيهات المتطوعين'), default=False)
    
    # تفضيلات طريقة التوصيل
    receive_push_notifications = models.BooleanField(_('الإشعارات الدفعية'), default=True)
    receive_email_notifications = models.BooleanField(_('الإشعارات بالبريد'), default=True)
    receive_sms_notifications = models.BooleanField(_('الإشعارات بالرسائل'), default=False)
    
    # توقيت الإشعارات
    quiet_hours_start = models.TimeField(_('بداية ساعات الهدوء'), default='22:00')
    quiet_hours_end = models.TimeField(_('نهاية ساعات الهدوء'), default='07:00')
    quiet_hours_enabled = models.BooleanField(_('تفعيل ساعات الهدوء'), default=False)
    
    # تفضيلات اللغة
    preferred_language = models.CharField(
        _('اللغة المفضلة'), 
        max_length=10, 
        choices=[('ar', 'العربية'), ('en', 'الإنجليزية')],
        default='ar'
    )
    
    # تحديثات التطبيق
    app_update_frequency = models.CharField(
        _('تكرار تحديث التطبيق'),
        max_length=20,
        choices=[
            ('immediate', 'فوري'),
            ('daily', 'يومي'),
            ('weekly', 'أسبوعي'),
        ],
        default='daily'
    )
    
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تفضيل الإشعار')
        verbose_name_plural = _('تفضيلات الإشعارات')
    
    def __str__(self):
        return f"تفضيلات إشعارات: {self.user.email}"
    
    def is_quiet_hours(self):
        """التحقق إذا كان الوقت ضمن ساعات الهدوء"""
        if not self.quiet_hours_enabled:
            return False
        
        now = timezone.now().time()
        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # عبر منتصف الليل
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
    
    def can_send_notification(self, notification_type, priority='normal'):
        """التحقق إذا كان يمكن إرسال الإشعار"""
        # التحقق من النوع
        type_mapping = {
            'match_found': 'enable_match_notifications',
            'report_status_change': 'enable_report_updates',
            'report_reviewed': 'enable_report_updates',
            'message_from_admin': 'enable_admin_messages',
            'verification_status': 'enable_system_updates',
            'system_update': 'enable_system_updates',
            'volunteer_assignment': 'enable_volunteer_alerts',
            'urgent_alert': 'enable_urgent_alerts',
        }
        
        type_field = type_mapping.get(notification_type)
        if type_field and not getattr(self, type_field, True):
            return False
        
        # التنبيهات العاجلة تتجاوز ساعات الهدوء
        if priority != 'urgent' and self.is_quiet_hours():
            return False
        
        return True


class NotificationTemplate(models.Model):
    """قوالب الإشعارات"""
    template_name = models.CharField(_('اسم القالب'), max_length=100, unique=True)
    notification_type = models.CharField(
        _('نوع الإشعار'), 
        max_length=50, 
        choices=Notification.NotificationType.choices
    )
    
    # المحتوى
    title_ar = models.CharField(_('العنوان (عربي)'), max_length=255)
    title_en = models.CharField(_('العنوان (إنجليزي)'), max_length=255, blank=True)
    
    message_ar = models.TextField(_('النص (عربي)'))
    message_en = models.TextField(_('النص (إنجليزي)'), blank=True)
    
    # المتغيرات
    variables = models.JSONField(
        _('المتغيرات'),
        default=list,
        help_text='قائمة المتغيرات المستخدمة في القالب، مثال: {user_name}, {report_code}'
    )
    
    # الإجراءات
    default_action_url = models.CharField(_('رابط الإجراء الافتراضي'), max_length=500, blank=True)
    default_action_text_ar = models.CharField(_('نص الإجراء (عربي)'), max_length=100, blank=True)
    default_action_text_en = models.CharField(_('نص الإجراء (إنجليزي)'), max_length=100, blank=True)
    
    # الأولوية الافتراضية
    default_priority = models.CharField(
        _('الأولوية الافتراضية'), 
        max_length=20, 
        choices=Notification.PriorityLevel.choices,
        default='normal'
    )
    
    # صلاحية الإشعار (بالأيام)
    default_expiry_days = models.IntegerField(_('صلاحية الإشعار (أيام)'), default=7)
    
    # تفعيل/تعطيل
    is_active = models.BooleanField(_('نشط'), default=True)
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('قالب إشعار')
        verbose_name_plural = _('قوالب الإشعارات')
        ordering = ['template_name']
    
    def __str__(self):
        return f"{self.template_name} ({self.get_notification_type_display()})"
    
    def render(self, language='ar', variables=None):
        """توليد محتوى الإشعار من القالب"""
        variables = variables or {}
        
        if language == 'ar':
            title = self.title_ar
            message = self.message_ar
            action_text = self.default_action_text_ar
        else:
            title = self.title_en or self.title_ar
            message = self.message_en or self.message_ar
            action_text = self.default_action_text_en or self.default_action_text_ar
        
        # استبدال المتغيرات
        for key, value in variables.items():
            placeholder = '{' + key + '}'
            title = title.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))
            action_text = action_text.replace(placeholder, str(value))
        
        return {
            'title': title,
            'message': message,
            'action_text': action_text,
            'action_url': self.default_action_url,
            'priority': self.default_priority,
            'expires_at': timezone.now() + timezone.timedelta(days=self.default_expiry_days)
        }


class PushNotificationToken(models.Model):
    """رموز الإشعارات الدفعية للأجهزة"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_tokens')
    
    # معلومات الجهاز
    device_token = models.CharField(_('رمز الجهاز'), max_length=255, unique=True)
    device_type = models.CharField(
        _('نوع الجهاز'),
        max_length=20,
        choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')]
    )
    device_name = models.CharField(_('اسم الجهاز'), max_length=100, blank=True)
    device_model = models.CharField(_('موديل الجهاز'), max_length=100, blank=True)
    
    # معلومات التطبيق
    app_version = models.CharField(_('إصدار التطبيق'), max_length=50, blank=True)
    os_version = models.CharField(_('إصدار النظام'), max_length=50, blank=True)
    
    # الحالة
    is_active = models.BooleanField(_('نشط'), default=True)
    last_active = models.DateTimeField(_('آخر نشاط'), auto_now=True)
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('رمز إشعار دفعي')
        verbose_name_plural = _('رموز الإشعارات الدفعية')
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['device_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_type}"
    
    def update_activity(self):
        """تحديث وقت النشاط الأخير"""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])