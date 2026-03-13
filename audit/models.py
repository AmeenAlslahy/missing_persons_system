from django.db import models
from django.utils import timezone
from accounts.models import User

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'إضافة'),
        ('UPDATE', 'تعديل'),
        ('DELETE', 'حذف'),
        ('LOGIN', 'تسجيل دخول'),
        ('LOGOUT', 'تسجيل خروج'),
        ('STATUS_CHANGE', 'تغيير حالة'),
        ('REVIEW', 'مراجعة'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المستخدم')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='العملية')
    resource_type = models.CharField(max_length=100, verbose_name='نوع المورد')
    resource_id = models.CharField(max_length=100, verbose_name='معرف المورد', blank=True)
    
    # تفاصيل التغييرات
    data_before = models.JSONField(null=True, blank=True, verbose_name='البيانات السابقة')
    data_after = models.JSONField(null=True, blank=True, verbose_name='البيانات الجديدة')
    
    # معلومات تقنية
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='التاريخ والوقت')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='عنوان IP')
    user_agent = models.TextField(blank=True, verbose_name='معلومات المتصفح')
    
    class Meta:
        verbose_name = 'سجل العمليات'
        verbose_name_plural = 'سجلات العمليات'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
