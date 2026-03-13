from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from locations.models import Governorate, District, Uzlah
import uuid
from PIL import Image
import io
from django.core.files.base import ContentFile
import os
import logging

logger = logging.getLogger(__name__)

class Person(models.Model):
    """نموذج الشخص - بيانات ثابتة"""
    GENDER_CHOICES = [
        ('M', _('ذكر')),
        ('F', _('أنثى')),
    ]
    
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]
    BODY_BUILD_CHOICES = [
        ('slim', _('نحيف')),
        ('average', _('متوسط')),
        ('athletic', _('رياضي')),
        ('heavy', _('ممتلئ')),
    ]
    
    SKIN_COLOR_CHOICES = [
        ('light', _('فاتح')),
        ('fair', _('حنطي')),
        ('medium', _('متوسط')),
        ('olive', _('خمري')),
        ('brown', _('أسمر')),
        ('black', _('أسود')),
    ]
    
    HAIR_COLOR_CHOICES = [
        ('black', _('أسود')),
        ('brown', _('بني')),
        ('blonde', _('أشقر')),
        ('red', _('أحمر')),
        ('white', _('أبيض')),
        ('grey', _('رمادي')),
        ('bald', _('أصلع')),
    ]
    
    EYE_COLOR_CHOICES = [
        ('black', _('أسود')),
        ('brown', _('بني')),
        ('hazel', _('عسلي')),
        ('green', _('أخضر')),
        ('blue', _('أزرق')),
        ('grey', _('رمادي')),
    ]
    
    person_id = models.UUIDField(_('معرف الشخص'), default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    
    # الاسم (ثابت)
    first_name = models.CharField(_('الاسم الأول'), max_length=150)
    middle_name = models.CharField(_('الاسم الأوسط'), max_length=150, blank=True)
    last_name = models.CharField(_('اللقب'), max_length=150)
    
    # تاريخ الميلاد (ثابت)
    date_of_birth = models.DateField(_('تاريخ الميلاد'), null=True, blank=True)
    gender = models.CharField(_('الجنس'), max_length=10, choices=GENDER_CHOICES)
    
    # صفات ثابتة
    blood_type = models.CharField(_('فصيلة الدم'), max_length=3, choices=BLOOD_TYPE_CHOICES, blank=True)
    chronic_conditions = models.TextField(_('أمراض مزمنة'), blank=True, help_text=_('مثل: سكري، ضغط، ربو'))
    permanent_marks = models.TextField(_('علامات دائمة'), blank=True, help_text=_('ندوب، وشوم، علامات مميزة'))
    
    # موقع السكن (قد يتغير لكن نادراً)
    home_governorate = models.ForeignKey(
        Governorate, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('محافظة السكن'), related_name='residents'
    )
    home_district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('مديرية السكن'), related_name='residents'
    )
    home_uzlah = models.ForeignKey(
        Uzlah, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('عزلة السكن'), related_name='residents'
    )
    
    # مواصفات جسدية إضافية
    height = models.FloatField(_('الطول (سم)'), null=True, blank=True)
    weight = models.FloatField(_('الوزن (كجم)'), null=True, blank=True)
    body_build = models.CharField(_('البنية الجسدية'), max_length=20, choices=BODY_BUILD_CHOICES, blank=True)
    skin_color = models.CharField(_('لون البشرة'), max_length=20, choices=SKIN_COLOR_CHOICES, blank=True)
    hair_color = models.CharField(_('لون الشعر'), max_length=20, choices=HAIR_COLOR_CHOICES, blank=True)
    eye_color = models.CharField(_('لون العينين'), max_length=20, choices=EYE_COLOR_CHOICES, blank=True)
    description = models.TextField(_('وصف إضافي'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإضافة'), auto_now_add=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('شخص')
        verbose_name_plural = _('الأشخاص')
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['date_of_birth']),
        ]
    
    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)
    
    @property
    def age(self):
        """حساب العمر الحالي"""
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def __str__(self):
        return self.full_name


class Report(models.Model):
    """نموذج البلاغ - بيانات متغيرة"""
    REPORT_TYPES = [
        ('missing', _('مفقود')),
        ('found', _('معثور عليه')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('قيد المراجعة')),
        ('active', _('نشط')),
        ('resolved', _('تم الحل')),
        ('closed', _('مغلق')),
        ('rejected', _('مرفوض')),
    ]
    
    IMPORTANCE_CHOICES = [
        ('low', _('منخفضة')),
        ('medium', _('متوسطة')),
        ('high', _('عالية')),
    ]
    
    report_id = models.UUIDField(_('معرف البلاغ'), default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    report_code = models.CharField(_('كود البلاغ'), max_length=50, unique=True)
    
    # الربط
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports', verbose_name=_('المبلغ'))
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='reports', verbose_name=_('الشخص'))
    
    # نوع البلاغ
    report_type = models.CharField(_('نوع البلاغ'), max_length=10, choices=REPORT_TYPES)
    
    # موقع الفقدان/العثور
    lost_governorate = models.ForeignKey(
        Governorate, on_delete=models.PROTECT,
        verbose_name=_('محافظة الفقدان/العثور'), related_name='reports'
    )
    lost_district = models.ForeignKey(
        District, on_delete=models.PROTECT,
        verbose_name=_('مديرية الفقدان/العثور'), related_name='reports'
    )
    lost_uzlah = models.ForeignKey(
        Uzlah, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('عزلة الفقدان/العثور'), related_name='reports'
    )
    lost_location_details = models.TextField(_('تفاصيل الموقع'), blank=True)
    
    # تاريخ ووقت آخر مشاهدة/عثور
    last_seen_date = models.DateField(_('تاريخ آخر مشاهدة/عثور'))
    last_seen_time = models.TimeField(_('وقت آخر مشاهدة/عثور'), null=True, blank=True)
    
    # حالة وقت الفقدان/العثور
    health_at_loss = models.CharField(_('الحالة الصحية وقت الفقدان/العثور'), max_length=255)
    medications = models.TextField(_('أدوية يتناولها'), blank=True)
    clothing_description = models.TextField(_('وصف الملابس'), blank=True)
    possessions = models.TextField(_('ممتلكات معه'), blank=True)
    
    # معلومات الاتصال بالبلاغ
    contact_phone = models.CharField(_('هاتف الاتصال'), max_length=20)
    contact_person = models.CharField(_('جهة الاتصال'), max_length=150, blank=True)
    
    # حالة البلاغ
    status = models.CharField(_('حالة البلاغ'), max_length=10, choices=STATUS_CHOICES, default='pending')
    importance = models.CharField(_('مستوى الأهمية'), max_length=10, choices=IMPORTANCE_CHOICES, default='medium')
    
    # تواريخ
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    resolved_at = models.DateTimeField(_('تاريخ الحل'), null=True, blank=True)
    close_reason = models.TextField(_('سبب الإغلاق'), blank=True)
    
    class Meta:
        verbose_name = _('بلاغ')
        verbose_name_plural = _('البلاغات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_code']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['lost_governorate', 'lost_district']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.report_code:
            # Generate a unique report code
            # Format: REP-YYYYMMDD-RANDOM
            import random
            import string
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.report_code = f"REP-{date_str}-{random_str}"
            
        super().save(*args, **kwargs)

    @property
    def age_at_loss(self):
        """العمر وقت الفقدان/العثور"""
        if self.person and self.person.date_of_birth and self.last_seen_date:
            age = self.last_seen_date.year - self.person.date_of_birth.year
            # تصحيح إذا لم يأتِ عيد ميلاده بعد
            if (self.last_seen_date.month, self.last_seen_date.day) < (self.person.date_of_birth.month, self.person.date_of_birth.day):
                age -= 1
            return age
        return None
    
    def __str__(self):
        return f"{self.report_code} - {self.person.full_name}"


class ReportImage(models.Model):
    """صور البلاغ"""
    image_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='images', verbose_name=_('البلاغ'))
    image_path = models.ImageField(_('الصورة'), upload_to='reports/images/%Y/%m/')
    face_embedding = models.JSONField(_('بصمة الوجه'), null=True, blank=True)
    quality_score = models.FloatField(_('جودة الصورة'), null=True, blank=True)
    upload_at = models.DateTimeField(_('تاريخ الرفع'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('صورة البلاغ')
        verbose_name_plural = _('صور البلاغات')
        ordering = ['-upload_at']
    
    def save(self, *args, **kwargs):
        if self.pk is None or (self.image_path and hasattr(self.image_path, 'file')):
            try:
                self.compress_image()
            except Exception as e:
                logger.error(f"Error compressing image: {e}")
        super().save(*args, **kwargs)
    
    def compress_image(self):
        try:
            if not self.image_path or not hasattr(self.image_path, 'path'):
                return
            
            img = Image.open(self.image_path.path)
            max_size = (800, 800)
            if img.height > max_size[1] or img.width > max_size[0]:
                img.thumbnail(max_size, Image.LANCZOS)
            
            output = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(output, format='JPEG', quality=70, optimize=True)
            output.seek(0)
            
            original_name = os.path.basename(self.image_path.name)
            new_name = os.path.splitext(original_name)[0] + '.jpg'
            self.image_path.save(new_name, ContentFile(output.read()), save=False)
            
        except Exception as e:
            logger.error(f"Error compressing image: {e}")