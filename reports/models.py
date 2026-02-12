from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from accounts.models import User
import uuid


class Report(models.Model):
    """نموذج البلاغات"""
    
    # أنواع البلاغات
    class ReportType(models.TextChoices):
        MISSING = 'missing', _('شخص مفقود')
        FOUND = 'found', _('شخص تم العثور عليه')
    
    # الجنس
    class Gender(models.TextChoices):
        MALE = 'M', _('ذكر')
        FEMALE = 'F', _('أنثى')
        UNKNOWN = 'U', _('غير معروف')
    
    # حالة البلاغ
    class Status(models.TextChoices):
        PENDING = 'pending', _('قيد المراجعة')
        ACTIVE = 'active', _('نشط')
        RESOLVED = 'resolved', _('تم الحل')
        CLOSED = 'closed', _('مغلق')
        REJECTED = 'rejected', _('مرفوض')
    
    # مستويات الأهمية
    class ImportanceLevel(models.TextChoices):
        HIGH = 'high', _('مرتفع')
        MEDIUM = 'medium', _('متوسط')
        LOW = 'low', _('منخفض')

    # الفئات العمرية
    class AgeGroup(models.TextChoices):
        INFANT = 'infant', _('رضيع')
        CHILD = 'child', _('طفل')
        TEEN = 'teen', _('مراهق')
        ADULT = 'adult', _('بالغ')
        SENIOR = 'senior', _('مسن')

    # الصفات الجسدية
    class BodyBuild(models.TextChoices):
        SLIM = 'slim', _('نحيف')
        AVERAGE = 'average', _('متوسط')
        ATHLETIC = 'athletic', _('رياضي')
        HEAVY = 'heavy', _('ممتلئ')

    class SkinColor(models.TextChoices):
        LIGHT = 'light', _('فاتح')
        FAIR = 'fair', _('حنطي')
        MEDIUM = 'medium', _('متوسط')
        OLIVE = 'olive', _('خمري')
        BROWN = 'brown', _('أسمر')
        BLACK = 'black', _('أسود')

    class EyeColor(models.TextChoices):
        BLACK = 'black', _('أسود')
        BROWN = 'brown', _('بني')
        HAZEL = 'hazel', _('عسلي')
        GREEN = 'green', _('أخضر')
        BLUE = 'blue', _('أزرق')
        GREY = 'grey', _('رمادي')

    class HairColor(models.TextChoices):
        BLACK = 'black', _('أسود')
        BROWN = 'brown', _('بني')
        BLONDE = 'blonde', _('أشقر')
        RED = 'red', _('أحمر')
        WHITE = 'white', _('أبيض')
        GREY = 'grey', _('رمادي')
        BALD = 'bald', _('أصلع')

    class HairType(models.TextChoices):
        STRAIGHT = 'straight', _('ناعم')
        WAVY = 'wavy', _('مموج')
        CURLY = 'curly', _('مجعد')
        COILY = 'coily', _('خشن')
    
    # معرفات فريدة
    report_id = models.UUIDField(_('معرف البلاغ'), default=uuid.uuid4, editable=False, unique=True)
    report_code = models.CharField(_('كود البلاغ'), max_length=50, unique=True, editable=False)
    
    # العلاقات
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports', verbose_name=_('المستخدم'))
    
    # نوع البلاغ (مفقود/معثور)
    report_type = models.CharField(
        _('نوع البلاغ'), 
        max_length=20, 
        choices=ReportType.choices,
        default=ReportType.MISSING
    )
    
    # ========== معلومات الشخص ==========
    person_name = models.CharField(_('اسم الشخص'), max_length=255)
    age = models.IntegerField(_('العمر'), null=True, blank=True)
    age_group = models.CharField(
        _('الفئة العمرية'), 
        max_length=20, 
        choices=AgeGroup.choices, 
        null=True, 
        blank=True
    )
    gender = models.CharField(_('الجنس'), max_length=1, choices=Gender.choices, default=Gender.UNKNOWN)
    nationality = models.CharField(_('الجنسية'), max_length=100, blank=True, default='')
    
    # الصور
    primary_photo = models.ImageField(
        _('الصورة الرئيسية'), 
        upload_to='reports/photos/',
        null=True,
        blank=True
    )
    additional_photos = models.JSONField(
        _('صور إضافية'),
        default=list,
        blank=True
    )
    
    # ========== الوصف البدني التفصيلي ==========
    height = models.DecimalField(_('الطول (سم)'), max_digits=5, decimal_places=1, null=True, blank=True)
    weight = models.DecimalField(_('الوزن (كجم)'), max_digits=5, decimal_places=1, null=True, blank=True)
    
    body_build = models.CharField(
        _('البنية الجسدية'), 
        max_length=50, 
        choices=BodyBuild.choices,
        blank=True
    )
    skin_color = models.CharField(
        _('لون البشرة'), 
        max_length=50, 
        choices=SkinColor.choices,
        blank=True
    )
    eye_color = models.CharField(
        _('لون العينين'), 
        max_length=50, 
        choices=EyeColor.choices,
        blank=True
    )
    hair_color = models.CharField(
        _('لون الشعر'), 
        max_length=50, 
        choices=HairColor.choices,
        blank=True
    )
    hair_type = models.CharField(
        _('نوع الشعر'), 
        max_length=50, 
        choices=HairType.choices,
        blank=True
    )
    
    # ملامح مميزة
    distinctive_features = models.TextField(_('ملامح مميزة'), blank=True)
    clothing_description = models.TextField(_('وصف الملابس'), blank=True, default='')
    scars_marks = models.TextField(_('ندوب أو علامات'), blank=True)
    tattoos = models.TextField(_('الوشوم'), blank=True)
    
    # ========== معلومات الفقدان/العثور ==========
    last_seen_location = models.CharField(_('آخر مكان رؤيته'), max_length=500)
    last_seen_date = models.DateField(_('تاريخ آخر رؤية'), default=timezone.now)
    last_seen_time = models.TimeField(_('وقت آخر رؤية'), null=True, blank=True)
    
    # للمفقودين
    missing_from = models.CharField(_('مفقود من'), max_length=255, blank=True)
    circumstances = models.TextField(_('ظروف الفقدان'), blank=True)
    
    # للمعثور عليهم
    found_location = models.CharField(_('مكان العثور'), max_length=500, blank=True)
    found_date = models.DateField(_('تاريخ العثور'), null=True, blank=True)
    current_location = models.CharField(_('المكان الحالي'), max_length=500, blank=True)
    health_condition = models.TextField(_('الحالة الصحية'), blank=True)
    
    # ========== معلومات الاتصال ==========
    contact_person = models.CharField(_('اسم جهة الاتصال'), max_length=255, blank=True)
    contact_phone = models.CharField(_('هاتف الاتصال'), max_length=20)
    contact_email = models.EmailField(_('بريد الاتصال'), blank=True)
    contact_relationship = models.CharField(_('صلة القرابة'), max_length=100, blank=True)
    
    # ========== حالة البلاغ ==========
    status = models.CharField(
        _('حالة البلاغ'), 
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    requires_admin_review = models.BooleanField(_('يتطلب مراجعة مشرف'), default=False)
    importance_level = models.CharField(
        _('درجة الأهمية'),
        max_length=20,
        choices=ImportanceLevel.choices,
        default=ImportanceLevel.MEDIUM
    )
    
    # التواريخ المهمة
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    resolved_at = models.DateTimeField(_('تاريخ الحل'), null=True, blank=True)
    
    # إحصائيات وخصوصية
    view_count = models.IntegerField(_('عدد المشاهدات'), default=0)
    last_viewed = models.DateTimeField(_('آخر مشاهدة'), null=True, blank=True)
    is_sensitive = models.BooleanField(_('محتوى حساس'), default=False, help_text=_('للأطفال والنساء والحالات الخاصة'))
    
    # مراجعة المشرف
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_reports',
        verbose_name=_('تمت المراجعة بواسطة')
    )
    reviewed_at = models.DateTimeField(_('تاريخ المراجعة'), null=True, blank=True)
    review_notes = models.TextField(_('ملاحظات المراجعة'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True, null=True)
    close_reason = models.TextField(_('سبب الإغلاق'), blank=True, null=True)
    
    # معلومات جغرافية
    latitude = models.DecimalField(_('خط العرض'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_('خط الطول'), max_digits=9, decimal_places=6, null=True, blank=True)
    city = models.CharField(_('المدينة'), max_length=100, blank=True)
    district = models.CharField(_('الحي/المنطقة'), max_length=100, blank=True)
    
    # دمج البلاغات
    merged_into = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merged_reports',
        verbose_name=_('دمج في بلاغ')
    )
    
    class Meta:
        verbose_name = _('بلاغ')
        verbose_name_plural = _('البلاغات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['person_name']),
            models.Index(fields=['last_seen_date']),
            models.Index(fields=['city', 'district']),
            models.Index(fields=['status', 'requires_admin_review']),
        ]
    
    def __str__(self):
        return f"{self.report_code} - {self.person_name} ({self.get_report_type_display()})"
    
    def save(self, *args, **kwargs):
        """توليد كود البلاغ تلقائياً عند الإنشاء والتحقق من المراجعة"""
        if not self.report_code:
            # إذا كان تاريخ الفقدان في الماضي (أصغر من اليوم)، يتطلب مراجعة المشرف
            check_date = self.last_seen_date
            if hasattr(check_date, 'date'): # if it's a datetime
                check_date = check_date.date()
                
            if check_date and check_date < timezone.now().date():
                self.requires_admin_review = True
                self.status = self.Status.PENDING
            
            # توليد كود مثل: MISS-2024-001 أو FND-2024-001
            prefix = 'MISS' if self.report_type == 'missing' else 'FND'
            year = timezone.now().year
            
            # الحصول على آخر رقم للعام الحالي
            last_report = Report.objects.filter(
                report_code__startswith=f'{prefix}-{year}-'
            ).order_by('-report_code').first()
            
            if last_report:
                last_number = int(last_report.report_code.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.report_code = f"{prefix}-{year}-{new_number:03d}"
        
        super().save(*args, **kwargs)
    
    def get_age_display(self):
        """عرض العمر مع الوحدة"""
        if self.age:
            return f"{self.age} سنة"
        return "غير معروف"
    
    def get_full_address(self):
        """الحصول على العنوان الكامل"""
        address_parts = []
        if self.district:
            address_parts.append(self.district)
        if self.city:
            address_parts.append(self.city)
        return '، '.join(address_parts) if address_parts else "غير محدد"
    
    def update_status(self, new_status, reviewed_by=None, notes=''):
        """تحديث حالة البلاغ"""
        self.status = new_status
        
        if new_status == self.Status.RESOLVED:
            self.resolved_at = timezone.now()
        
        if reviewed_by:
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.review_notes = notes
        
        self.save()


class ReportImage(models.Model):
    """الصور المرتبطة بالبلاغات"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='images', verbose_name=_('البلاغ'))
    image = models.ImageField(_('الصورة'), upload_to='reports/images/')
    
    # معالجة الذكاء الاصطناعي
    face_embedding = models.JSONField(_('بصمة الوجه'), null=True, blank=True)
    embedding_version = models.CharField(_('إصدار النموذج'), max_length=50, blank=True)
    face_detected = models.BooleanField(_('تم اكتشاف الوجه'), default=False)
    quality_score = models.FloatField(_('جودة الصورة'), null=True, blank=True)
    
    # بيانات وصفية
    uploaded_at = models.DateTimeField(_('تاريخ الرفع'), auto_now_add=True)
    processed_at = models.DateTimeField(_('تاريخ المعالجة'), null=True, blank=True)
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
    
    class Meta:
        verbose_name = _('صورة بلاغ')
        verbose_name_plural = _('صور البلاغات')
    
    def __str__(self):
        return f"صورة لـ {self.report.person_name}"


class Category(models.Model):
    """تصنيف البلاغات (أطفال، كبار سن، ذوي إعاقة)"""
    name = models.CharField(_('اسم الفئة'), max_length=100, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    priority_level = models.IntegerField(_('مستوى الأولوية'), default=1)  # 1-5
    response_time_hours = models.IntegerField(_('وقت الاستجابة المستهدف (ساعات)'), default=24)
    special_procedures = models.TextField(_('إجراءات خاصة'), blank=True)
    icon = models.CharField(_('الأيقونة'), max_length=50, blank=True)
    
    class Meta:
        verbose_name = _('فئة')
        verbose_name_plural = _('الفئات')
    
    def __str__(self):
        return self.name


class ReportCategory(models.Model):
    """ربط البلاغات بالفئات"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='categories')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['report', 'category']
        verbose_name = _('تصنيف البلاغ')
        verbose_name_plural = _('تصنيفات البلاغات')
    
    def __str__(self):
        return f"{self.report.person_name} - {self.category.name}"


class GeographicalArea(models.Model):
    """المناطق الجغرافية للتنسيق"""
    area_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    area_name = models.CharField(_('اسم المنطقة'), max_length=100)
    city = models.CharField(_('المدينة'), max_length=100)
    
    # إحداثيات جغرافية
    center_latitude = models.DecimalField(_('خط العرض المركزي'), max_digits=9, decimal_places=6)
    center_longitude = models.DecimalField(_('خط الطول المركزي'), max_digits=9, decimal_places=6)
    radius_km = models.DecimalField(_('نصف القطر (كم)'), max_digits=5, decimal_places=2, default=5.0)
    boundary_coordinates = models.JSONField(_('حدود المنطقة'), blank=True, null=True)
    
    # إحصائيات
    active_volunteers = models.IntegerField(_('المتطوعين النشطين'), default=0)
    active_reports = models.IntegerField(_('البلاغات النشطة'), default=0)
    
    # معلومات الاتصال
    coordinator_name = models.CharField(_('اسم المنسق'), max_length=255, blank=True)
    coordinator_phone = models.CharField(_('هاتف المنسق'), max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('منطقة جغرافية')
        verbose_name_plural = _('المناطق الجغرافية')
        unique_together = ['area_name', 'city']
    
    def __str__(self):
        return f"{self.area_name} - {self.city}"


class ReportAuditLog(models.Model):
    """سجل تدقيق للبلاغات"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='report_audit_logs')
    
    action_type = models.CharField(_('نوع العملية'), max_length=50)
    action_details = models.TextField(_('تفاصيل العملية'))
    
    # تغييرات البيانات
    old_data = models.JSONField(_('البيانات القديمة'), null=True, blank=True)
    new_data = models.JSONField(_('البيانات الجديدة'), null=True, blank=True)
    changed_fields = models.JSONField(_('الحقول المتغيرة'), null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    user_agent = models.TextField(_('معلومات المتصفح'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ العملية'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل تدقيق البلاغ')
        verbose_name_plural = _('سجلات تدقيق البلاغات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.report.report_code} - {self.action_type} - {self.created_at}"