from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid
from .fields import EncryptedCharField

class UserManager(BaseUserManager):
    """مدير مخصص لنموذج المستخدم"""
    
    def create_user(self, email, full_name, password=None, **extra_fields):
        """إنشاء مستخدم عادي"""
        if not email:
            raise ValueError(_('يجب إدخال البريد الإلكتروني'))
        if not full_name:
            raise ValueError(_('يجب إدخال الاسم الكامل'))
            
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, full_name, password=None, **extra_fields):
        """إنشاء مستخدم مدير"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('verification_status', 'verified')
        extra_fields.setdefault('user_role', 'super_admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('المستخدم المدير يجب أن يكون is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('المستخدم المدير يجب أن يكون is_superuser=True'))
            
        return self.create_user(email, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """نموذج المستخدم المخصص"""
    
    class Role(models.TextChoices):
        USER = 'user', _('مستخدم عادي')
        VOLUNTEER = 'volunteer', _('متطوع')
        ADMIN = 'admin', _('مشرف')
        SUPER_ADMIN = 'super_admin', _('مشرف رئيسي')
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', _('في انتظار التحقق')
        VERIFIED = 'verified', _('مؤكد الهوية')
        REJECTED = 'rejected', _('مرفوض')
    
    class Gender(models.TextChoices):
        MALE = 'M', _('ذكر')
        FEMALE = 'F', _('أنثى')
    
    email = models.EmailField(_('البريد الإلكتروني'), unique=True)
    full_name = models.CharField(_('الاسم الكامل'), max_length=255)
    national_id = EncryptedCharField(_('رقم الهوية الوطنية'), max_length=255, null=True, blank=True, unique=True)
    date_of_birth = models.DateField(_('تاريخ الميلاد'), null=True, blank=True)
    gender = models.CharField(_('الجنس'), max_length=1, choices=Gender.choices, null=True, blank=True)
    phone = EncryptedCharField(_('رقم الهاتف'), max_length=255, null=True, blank=True)
    
    # السكن
    governorate = models.CharField(_('المحافظة'), max_length=100, null=True, blank=True)
    district = models.CharField(_('المديرية'), max_length=100, null=True, blank=True)
    uzlah = models.CharField(_('العزلة'), max_length=100, null=True, blank=True)
    
    user_role = models.CharField(
        _('دور المستخدم'), 
        max_length=20, 
        choices=Role.choices, 
        default=Role.USER
    )
    
    # التحقق والأمان
    verification_date = models.DateTimeField(_('تاريخ التحقق'), null=True, blank=True)
    verified_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('تم التحقق بواسطة'))
    two_factor_enabled = models.BooleanField(_('المصادقة الثنائية'), default=False)
    last_password_change = models.DateTimeField(_('آخر تغيير لكلمة المرور'), auto_now_add=True)

    verification_status = models.CharField(
        _('حالة التحقق'), 
        max_length=20, 
        choices=VerificationStatus.choices, 
        default=VerificationStatus.PENDING
    )
    
    is_active = models.BooleanField(_('نشط'), default=True)
    is_blocked = models.BooleanField(_('محظور'), default=False)
    blocking_reason = models.TextField(_('سبب الحظر'), null=True, blank=True)
    is_staff = models.BooleanField(_('موظف'), default=False)
    date_joined = models.DateTimeField(_('تاريخ الانضمام'), default=timezone.now)
    last_login = models.DateTimeField(_('آخر دخول'), null=True, blank=True)
    
    trust_score = models.FloatField(_('درجة الثقة'), default=0.0)
    total_reports = models.IntegerField(_('عدد البلاغات'), default=0)
    resolved_reports = models.IntegerField(_('البلاغات المحلولة'), default=0)
    
    profile_picture = models.ImageField(
        _('الصورة الشخصية'), 
        upload_to='profiles/', 
        null=True, 
        blank=True
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمين')
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    def update_trust_score(self):
        """تحديث درجة الثقة"""
        if self.total_reports > 0:
            self.trust_score = (self.resolved_reports / self.total_reports) * 100
        else:
            self.trust_score = 0.0
        self.save(update_fields=['trust_score'])


class VolunteerProfile(models.Model):
    """الملف الشخصي للمتطوع"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer_profile')
    city = models.CharField(_('المدينة'), max_length=100, null=True, blank=True)
    area = models.CharField(_('المنطقة'), max_length=100, null=True, blank=True)
    is_active_volunteer = models.BooleanField(_('متطوع نشط'), default=True)
    volunteer_since = models.DateField(_('متطوع منذ'), default=timezone.now)
    total_contributions = models.IntegerField(_('إجمالي المساهمات'), default=0)
    skills = models.JSONField(_('المهارات'), default=list, blank=True)
    languages = models.JSONField(_('اللغات'), default=list, blank=True)
    availability_hours = models.JSONField(_('ساعات التوفر'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('ملف المتطوع')
        verbose_name_plural = _('ملفات المتطوعين')


class AuditLog(models.Model):
    """سجل التدقيق للمستخدمين"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action_type = models.CharField(_('نوع العملية'), max_length=50)
    action_details = models.TextField(_('تفاصيل العملية'))
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    user_agent = models.TextField(_('معلومات المتصفح'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ العملية'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل تدقيق')
        verbose_name_plural = _('سجلات التدقيق')
        ordering = ['-created_at']