from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from accounts.models import User
import uuid


class FaceEmbedding(models.Model):
    """متجهات الوجه المحفوظة"""
    image = models.OneToOneField(
        'reports.ReportImage', 
        on_delete=models.CASCADE, 
        related_name='face_embedding_obj',
        verbose_name=_('الصورة')
    )
    
    # المتجه الرقمي للوجه (يمكن تخزينه كـ JSON أو Binary)
    embedding_vector = models.JSONField(_('متجه البصمة'))
    embedding_version = models.CharField(_('إصدار النموذج'), max_length=50, default='v1.0')
    
    # معلومات إضافية
    face_count = models.IntegerField(_('عدد الوجوه المكتشفة'), default=0)
    face_analysis = models.JSONField(_('تحليل الوجه'), blank=True, null=True)
    
    # الجودة
    quality_score = models.FloatField(_('درجة الجودة'), default=0.0)
    confidence_score = models.FloatField(_('درجة الثقة'), default=0.0)
    
    # الحالة
    processing_status = models.CharField(
        _('حالة المعالجة'),
        max_length=20,
        choices=[
            ('pending', 'في الانتظار'),
            ('processing', 'قيد المعالجة'),
            ('completed', 'مكتملة'),
            ('failed', 'فشلت'),
        ],
        default='pending'
    )
    
    # التواريخ
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    processed_at = models.DateTimeField(_('تاريخ المعالجة'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('بصمة وجه')
        verbose_name_plural = _('بصمات الوجوه')
        indexes = [
            models.Index(fields=['processing_status', 'created_at']),
            models.Index(fields=['quality_score']),
        ]
    
    def __str__(self):
        return f"بصمة لـ {self.image.report.person_name}"


class MatchResult(models.Model):
    """نتائج المطابقة بين البلاغات"""
    
    # أنواع المطابقة
    class MatchType(models.TextChoices):
        AUTO = 'auto', _('تلقائي')
        MANUAL = 'manual', _('يدوي')
        ADMIN = 'admin', _('مشرف')
    
    # حالة المطابقة
    class MatchStatus(models.TextChoices):
        PENDING = 'pending', _('قيد المراجعة')
        REVIEWING = 'reviewing', _('قيد التحقق')
        ACCEPTED = 'accepted', _('مقبول')
        REJECTED = 'rejected', _('مرفوض')
        FALSE_POSITIVE = 'false_positive', _('إيجابي خاطئ')
    
    # مستوى الثقة
    class ConfidenceLevel(models.TextChoices):
        VERY_HIGH = 'very_high', _('عالي جداً')
        HIGH = 'high', _('عالي')
        MEDIUM = 'medium', _('متوسط')
        LOW = 'low', _('منخفض')

    class PriorityLevel(models.TextChoices):
        URGENT = 'urgent', _('عاجل (طفل/مسن)')
        HIGH = 'high', _('مرتفع')
        NORMAL = 'normal', _('عادي')
    
    match_id = models.UUIDField(_('معرف المطابقة'), default=uuid.uuid4, editable=False, unique=True)
    
    # البلاغات المتطابقة
    missing_report = models.ForeignKey(
        'reports.Report', 
        on_delete=models.CASCADE, 
        related_name='matches_as_missing',
        verbose_name=_('بلاغ المفقود')
    )
    found_report = models.ForeignKey(
        'reports.Report', 
        on_delete=models.CASCADE, 
        related_name='matches_as_found',
        verbose_name=_('بلاغ المعثور عليه')
    )
    
    # النتائج
    similarity_score = models.FloatField(_('درجة التشابه'), help_text='بين 0.0 و 1.0')
    confidence_score = models.FloatField(_('درجة الثقة'), help_text='بين 0 و 100')
    confidence_level = models.CharField(
        _('مستوى الثقة'), 
        max_length=20, 
        choices=ConfidenceLevel.choices,
        default=ConfidenceLevel.MEDIUM
    )
    
    # النوع والحالة
    match_type = models.CharField(
        _('نوع المطابقة'), 
        max_length=20, 
        choices=MatchType.choices,
        default=MatchType.AUTO
    )
    match_status = models.CharField(
        _('حالة المطابقة'), 
        max_length=20, 
        choices=MatchStatus.choices,
        default=MatchStatus.PENDING
    )
    
    # المراجعة
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_matches',
        verbose_name=_('تمت المراجعة بواسطة')
    )
    reviewed_at = models.DateTimeField(_('تاريخ المراجعة'), null=True, blank=True)
    review_notes = models.TextField(_('ملاحظات المراجعة'), blank=True)
    
    # التفاصيل
    match_details = models.JSONField(_('تفاصيل المطابقة'), blank=True, null=True)
    matched_features = models.JSONField(_('المميزات المتطابقة'), blank=True, null=True)
    
    # التواصل
    communication_opened = models.BooleanField(_('تم فتح التواصل'), default=False)
    communication_details = models.JSONField(_('تفاصيل التواصل'), blank=True, null=True)
    
    # التواريخ
    detected_at = models.DateTimeField(_('تاريخ الكشف'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    resolved_at = models.DateTimeField(_('تاريخ الحل'), null=True, blank=True)

    # الأولوية والتحليل
    priority_level = models.CharField(
        _('مستوى الأولوية'),
        max_length=20,
        choices=PriorityLevel.choices,
        default=PriorityLevel.NORMAL
    )
    is_experimental = models.BooleanField(_('تجريبي'), default=False)

    # حقول إضافية للتحسين
    match_algorithm = models.CharField(_('خوارزمية المطابقة'), max_length=50, default='v1.0')
    match_confidence_breakdown = models.JSONField(_('تفاصيل درجة الثقة'), blank=True, null=True)
    human_reviewed = models.BooleanField(_('تمت المراجعة البشرية'), default=False)
    review_evidence = models.JSONField(_('أدلة المراجعة'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('نتيجة مطابقة')
        verbose_name_plural = _('نتائج المطابقة')
        ordering = ['-similarity_score', '-detected_at']
        indexes = [
            models.Index(fields=['missing_report', 'found_report']),
            models.Index(fields=['similarity_score']),
            models.Index(fields=['match_status', 'confidence_level']),
            models.Index(fields=['detected_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['missing_report', 'found_report'],
                name='unique_match_pair'
            ),
            models.CheckConstraint(
                check=models.Q(similarity_score__gte=0) & models.Q(similarity_score__lte=1),
                name='similarity_score_range'
            ),
            models.CheckConstraint(
                check=models.Q(confidence_score__gte=0) & models.Q(confidence_score__lte=100),
                name='confidence_score_range'
            ),
        ]
    
    def __str__(self):
        return f"مطابقة: {self.missing_report.person_name} ←→ {self.found_report.person_name} ({self.similarity_score:.2%})"
    
    def save(self, *args, **kwargs):
        """تحديث مستوى الثقة والأولوية"""
        # تحديث مستوى الثقة بناءً على الدرجة الرقمية
        if self.confidence_score >= 90:
            self.confidence_level = self.ConfidenceLevel.VERY_HIGH
        elif self.confidence_score >= 75:
            self.confidence_level = self.ConfidenceLevel.HIGH
        elif self.confidence_score >= 50:
            self.confidence_level = self.ConfidenceLevel.MEDIUM
        else:
            self.confidence_level = self.ConfidenceLevel.LOW
        
        # تحديث الأولوية بناءً على خصائص الشخص
        # الأطفال (أقل من 12) والمسنون (أكبر من 60) هم أولوية قصوى
        p1 = self.missing_report
        p2 = self.found_report
        
        is_child = (p1.age and p1.age < 12) or (p2.age and p2.age < 12) or \
                   (p1.age_group == 'infant' or p1.age_group == 'child')
        is_senior = (p1.age and p1.age > 60) or (p2.age and p2.age > 60) or \
                    (p1.age_group == 'senior')
        
        if is_child or is_senior:
            self.priority_level = self.PriorityLevel.URGENT
        elif p1.importance_level == 'high' or p2.importance_level == 'high':
            self.priority_level = self.PriorityLevel.HIGH
        
        super().save(*args, **kwargs)
    
    def accept_match(self, user, notes=''):
        """قبول المطابقة"""
        self.match_status = self.MatchStatus.ACCEPTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
        
        # تحديث حالة البلاغات
        self.missing_report.status = Report.Status.RESOLVED
        self.missing_report.resolved_at = timezone.now()
        self.missing_report.save()
        
        self.found_report.status = Report.Status.RESOLVED
        self.found_report.resolved_at = timezone.now()
        self.found_report.save()
    
    def reject_match(self, user, notes='', false_positive=False):
        """رفض المطابقة"""
        if false_positive:
            self.match_status = self.MatchStatus.FALSE_POSITIVE
        else:
            self.match_status = self.MatchStatus.REJECTED
        
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class MatchReview(models.Model):
    """مراجعة المطابقة من قبل المشرف"""
    match = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_reviews')
    
    # القرار
    decision = models.CharField(
        _('القرار'),
        max_length=20,
        choices=[
            ('accept', 'قبول'),
            ('reject', 'رفض'),
            ('need_more_info', 'بحاجة لمزيد من المعلومات'),
        ]
    )
    
    # التفاصيل
    notes = models.TextField(_('ملاحظات المراجعة'), blank=True)
    evidence_links = models.JSONField(_('روابط الأدلة'), blank=True, null=True)
    
    # التواريخ
    reviewed_at = models.DateTimeField(_('تاريخ المراجعة'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مراجعة مطابقة')
        verbose_name_plural = _('مراجعات المطابقة')
        ordering = ['-reviewed_at']
    
    def __str__(self):
        return f"مراجعة: {self.match} - {self.get_decision_display()}"


class MatchingConfig(models.Model):
    """إعدادات نظام المطابقة"""
    config_name = models.CharField(_('اسم الإعداد'), max_length=100, unique=True)
    
    # العتبات
    similarity_threshold = models.FloatField(
        _('عتبة التشابه الدنيا'),
        default=0.32,
        help_text='الحد الأدنى لدرجة التشابه للاعتبار كتطابق محتمل'
    )
    confidence_threshold = models.FloatField(
        _('عتبة الثقة الدنيا'),
        default=70.0,
        help_text='الحد الأدنى لدرجة الثقة'
    )
    
    # إعدادات المطابقة
    enable_face_matching = models.BooleanField(_('تفعيل مطابقة الوجوه'), default=True)
    enable_data_matching = models.BooleanField(_('تفعيل مطابقة البيانات'), default=True)
    enable_hybrid_matching = models.BooleanField(_('تفعيل المطابقة الهجينة'), default=True)
    
    # الأوزان
    face_weight = models.FloatField(_('وزن مطابقة الوجوه'), default=0.7)
    data_weight = models.FloatField(_('وزن مطابقة البيانات'), default=0.3)
    
    # إعدادات الذكاء الاصطناعي
    ai_model_version = models.CharField(_('إصدار نموذج الذكاء الاصطناعي'), max_length=50, default='MobileNetV2_v1.0')
    embedding_size = models.IntegerField(_('حجم المتجه'), default=1280)
    
    # التحديث التلقائي
    auto_match_enabled = models.BooleanField(_('التطابق التلقائي'), default=True)
    match_interval_hours = models.IntegerField(_('فترة التطابق (ساعات)'), default=1)
    
    # الإشعارات
    notify_on_high_confidence = models.BooleanField(_('إشعار عند ثقة عالية'), default=True)
    notify_on_match = models.BooleanField(_('إشعار عند وجود تطابق'), default=True)
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_run_at = models.DateTimeField(_('آخر تشغيل'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('إعداد المطابقة')
        verbose_name_plural = _('إعدادات المطابقة')
    
    def __str__(self):
        return self.config_name
    
    def save(self, *args, **kwargs):
        """التحقق من أن مجموع الأوزان = 1"""
        if self.enable_hybrid_matching:
            total_weight = self.face_weight + self.data_weight
            if abs(total_weight - 1.0) > 0.01:  # نسبة خطأ صغيرة
                raise ValueError(f'مجموع الأوزان يجب أن يكون 1.0، القيمة الحالية: {total_weight}')
        
        super().save(*args, **kwargs)


class MatchingAuditLog(models.Model):
    """سجل تدقيق عمليات المطابقة"""
    log_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # نوع العملية
    action_type = models.CharField(
        _('نوع العملية'),
        max_length=50,
        choices=[
            ('MATCH_START', 'بدء عملية مطابقة'),
            ('MATCH_COMPLETE', 'اكتمال عملية مطابقة'),
            ('MATCH_FOUND', 'اكتشاف تطابق'),
            ('REVIEW_ACCEPT', 'قبول مراجعة'),
            ('REVIEW_REJECT', 'رفض مراجعة'),
            ('CONFIG_UPDATE', 'تحديث إعدادات'),
        ]
    )
    
    # التفاصيل
    action_details = models.TextField(_('تفاصيل العملية'))
    metadata = models.JSONField(_('بيانات إضافية'), blank=True, null=True)
    
    # المستخدم (إذا كان هناك مستخدم مسؤول)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_('المستخدم')
    )
    
    # التواريخ
    created_at = models.DateTimeField(_('تاريخ العملية'), auto_now_add=True)
    processing_time = models.FloatField(_('زمن المعالجة (ثواني)'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('سجل تدقيق المطابقة')
        verbose_name_plural = _('سجلات تدقيق المطابقة')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.action_type} - {self.created_at}"