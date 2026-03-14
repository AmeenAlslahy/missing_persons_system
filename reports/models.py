from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator, MinLengthValidator
from django_cryptography.fields import encrypt
from accounts.models import User
from locations.models import Governorate, District, Uzlah
import uuid
from PIL import Image
import io
from django.core.files.base import ContentFile
import os
import logging
from datetime import date
from dateutil.relativedelta import relativedelta

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
    
    person_id = models.UUIDField(_('معرف الشخص'), default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    
    first_name = models.CharField(_('الاسم الأول'), max_length=150, db_index=True)
    middle_name = models.CharField(_('الاسم الأوسط'), max_length=150, blank=True, db_index=True)
    last_name = models.CharField(_('اللقب'), max_length=150, db_index=True)
    
    date_of_birth = models.DateField(_('تاريخ الميلاد'), null=True, blank=True)
    gender = models.CharField(_('الجنس'), max_length=10, choices=GENDER_CHOICES, db_index=True)
    
    blood_type = models.CharField(_('فصيلة الدم'), max_length=3, choices=BLOOD_TYPE_CHOICES, blank=True)
    chronic_conditions = models.TextField(_('أمراض مزمنة'), blank=True)
    permanent_marks = models.TextField(_('علامات دائمة'), blank=True)
    
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
    
    created_at = models.DateTimeField(_('تاريخ الإضافة'), auto_now_add=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('شخص')
        verbose_name_plural = _('الأشخاص')
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['date_of_birth']),
            models.Index(fields=['gender']),
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
        """حساب العمر الحالي بدقة"""
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
    report_code = models.CharField(_('كود البلاغ'), max_length=50, unique=True, db_index=True)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports', verbose_name=_('المبلغ'))
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='reports', verbose_name=_('الشخص'))
    
    report_type = models.CharField(_('نوع البلاغ'), max_length=10, choices=REPORT_TYPES, db_index=True)
    
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
    
    last_seen_date = models.DateField(_('تاريخ آخر مشاهدة/عثور'), db_index=True)
    last_seen_time = models.TimeField(_('وقت آخر مشاهدة/عثور'), null=True, blank=True)
    
    health_at_loss = models.CharField(_('الحالة الصحية'), max_length=255)
    medications = models.TextField(_('أدوية يتناولها'), blank=True)
    clothing_description = models.TextField(_('وصف الملابس'), blank=True)
    possessions = models.TextField(_('ممتلكات معه'), blank=True)
    
    from accounts.fields import EncryptedCharField
    contact_phone = EncryptedCharField(_('هاتف الاتصال'), max_length=512)
    # contact_phone = encrypt(models.CharField(_('هاتف الاتصال'), max_length=255, validators=[MinLengthValidator(8)]))
    contact_person = models.CharField(_('جهة الاتصال'), max_length=150, blank=True)
    
    # الموافقة على الصور (للقاصرين والنساء)
    image_consent_given = models.BooleanField(_('تمت الموافقة على نشر الصور'), default=False)
    
    status = models.CharField(_('حالة البلاغ'), max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    importance = models.CharField(_('مستوى الأهمية'), max_length=10, choices=IMPORTANCE_CHOICES, default='medium')
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True, db_index=True)
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
            models.Index(fields=['status', 'report_type']),
            models.Index(fields=['last_seen_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.report_code:
            import random
            import string
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.report_code = f"REP-{date_str}-{random_str}"
        super().save(*args, **kwargs)

    @property
    def age_at_loss(self):
        """العمر وقت الفقدان/العثور بدقة"""
        if self.person and self.person.date_of_birth and self.last_seen_date:
            age = self.last_seen_date.year - self.person.date_of_birth.year
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
    image_path = models.ImageField(
        _('الصورة'), 
        upload_to='reports/images/%Y/%m/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    face_embedding = models.JSONField(_('بصمة الوجه'), null=True, blank=True)
    quality_score = models.FloatField(_('جودة الصورة'), null=True, blank=True)
    upload_at = models.DateTimeField(_('تاريخ الرفع'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('صورة البلاغ')
        verbose_name_plural = _('صور البلاغات')
        ordering = ['-upload_at']
        indexes = [
            models.Index(fields=['report', 'upload_at']),
        ]
    
    def save(self, *args, **kwargs):
        if self.pk is None:
            self.compress_image()
        super().save(*args, **kwargs)
    
    def compress_image(self, max_size_mb=2):
        """ضغط الصورة مع دعم التخزين السحابي"""
        try:
            if not self.image_path:
                return
            
            # فتح الصورة باستخدام BytesIO (يعمل مع كل أنواع التخزين)
            img_file = self.image_path.open()
            img = Image.open(img_file)
            
            max_dimensions = (1024, 1024)
            if img.height > max_dimensions[1] or img.width > max_dimensions[0]:
                img.thumbnail(max_dimensions, Image.LANCZOS)
            
            output = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # ضبط الجودة حسب حجم الملف
            quality = 85
            img.save(output, format='JPEG', quality=quality, optimize=True)
            
            # إذا كان الحجم كبيراً، نخفض الجودة أكثر
            if output.tell() > max_size_mb * 1024 * 1024:
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=60, optimize=True)
            
            output.seek(0)
            
            # حفظ الصورة المضغوطة
            new_name = os.path.basename(self.image_path.name).rsplit('.', 1)[0] + '.jpg'
            self.image_path.save(new_name, ContentFile(output.read()), save=False)
            
        except Exception as e:
            logger.error(f"Error compressing image {self.image_path.name}: {e}")
        finally:
            if 'img_file' in locals():
                img_file.close()