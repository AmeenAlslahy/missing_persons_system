from django.db import models
from reports.models import Report
import uuid
from django.utils.translation import gettext_lazy as _


class MatchResult(models.Model):
    """نتائج المطابقة بين بلاغين"""
    
    MATCH_STATUS = [
        ('pending', _('قيد المراجعة')),
        ('accepted', _('مقبول')),
        ('rejected', _('مرفوض')),
        ('false_positive', _('إيجابي خاطئ')),
        ('reviewing', _('قيد المراجعة اليدوية')),
    ]
    
    CONFIDENCE_LEVELS = [
        ('very_high', _('عالية جداً')),
        ('high', _('عالية')),
        ('medium', _('متوسطة')),
        ('low', _('منخفضة')),
    ]
    
    MATCH_TYPES = [
        ('auto', _('تلقائي')),
        ('manual', _('يدوي')),
    ]
    
    PRIORITY_LEVELS = [
        ('urgent', _('عاجل')),
        ('high', _('مرتفع')),
        ('normal', _('عادي')),
        ('low', _('منخفض')),
    ]
    
    match_id = models.UUIDField(_('معرف المطابقة'), default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    
    report_1 = models.ForeignKey(
        Report, on_delete=models.CASCADE, 
        related_name='matches_as_first', 
        verbose_name=_('البلاغ الأول')
    )
    report_2 = models.ForeignKey(
        Report, on_delete=models.CASCADE, 
        related_name='matches_as_second', 
        verbose_name=_('البلاغ الثاني')
    )
    
    similarity_score = models.FloatField(_('نسبة التشابه'), default=0.0)
    confidence_level = models.CharField(_('مستوى الثقة'), max_length=20, choices=CONFIDENCE_LEVELS, default='medium')
    match_type = models.CharField(_('نوع المطابقة'), max_length=20, choices=MATCH_TYPES, default='auto')
    match_status = models.CharField(_('حالة المطابقة'), max_length=20, choices=MATCH_STATUS, default='pending')
    priority_level = models.CharField(_('مستوى الأولوية'), max_length=20, choices=PRIORITY_LEVELS, default='normal')
    
    match_reason = models.TextField(_('سبب المطابقة'), blank=True)
    match_details = models.JSONField(_('تفاصيل المطابقة'), default=dict, blank=True)
    
    reviewed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='reviewed_matches',
        verbose_name=_('تمت المراجعة بواسطة')
    )
    reviewed_at = models.DateTimeField(_('تاريخ المراجعة'), null=True, blank=True)
    review_notes = models.TextField(_('ملاحظات المراجعة'), blank=True)
    
    detected_at = models.DateTimeField(_('تاريخ الاكتشاف'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('نتيجة مطابقة')
        verbose_name_plural = _('نتائج المطابقة')
        ordering = ['-similarity_score', '-detected_at']
        indexes = [
            models.Index(fields=['match_status']),
            models.Index(fields=['priority_level']),
            models.Index(fields=['detected_at']),
        ]

    def __str__(self):
        return f"مطابقة: {self.report_1.report_code} ↔ {self.report_2.report_code} ({self.similarity_score:.2f})"
    
    @property
    def missing_report(self):
        """الحصول على بلاغ المفقود (الافتراضي أن report_1 هو المفقود)"""
        return self.report_1 if self.report_1.report_type == 'missing' else self.report_2
    
    @property
    def found_report(self):
        """الحصول على بلاغ المعثور عليه"""
        return self.report_2 if self.report_1.report_type == 'missing' else self.report_1


class MatchingAuditLog(models.Model):
    """سجل لتدقيق عمليات المطابقة"""
    
    ACTION_TYPES = [
        ('batch_match', _('مطابقة مجمعة')),
        ('single_match', _('مطابقة فردية')),
        ('review', _('مراجعة')),
        ('reprocess', _('إعادة معالجة')),
    ]
    
    action_type = models.CharField(_('نوع الإجراء'), max_length=50, choices=ACTION_TYPES)
    report_count = models.IntegerField(_('عدد البلاغات'), default=0)
    processing_time = models.FloatField(_('وقت المعالجة (ثواني)'), default=0.0)
    status = models.CharField(_('الحالة'), max_length=50, default='success')
    message = models.TextField(_('الرسالة'), blank=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_('تم بواسطة')
    )
    timestamp = models.DateTimeField(_('وقت التنفيذ'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل تدقيق مطابقة')
        verbose_name_plural = _('سجل تدقيق المطابقات')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action_type} - {self.timestamp}"