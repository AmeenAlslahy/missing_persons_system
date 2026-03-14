from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, MinLengthValidator
from django_cryptography.fields import encrypt
import uuid
from locations.models import Governorate, District, Uzlah


class CustomUserManager(BaseUserManager):
    def create_user(self, phone, first_name, last_name, password=None, **extra_fields):
        if not phone:
            raise ValueError(_('يجب إدخال رقم الهاتف'))
        if not first_name or not last_name:
            raise ValueError(_('يجب إدخال الاسم الأول واللقب'))
        
        # تطبيع رقم الهاتف (إزالة المسافات)
        phone = phone.strip()
        
        user = self.model(
            phone=phone, 
            first_name=first_name.strip(), 
            last_name=last_name.strip(), 
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'super_admin')
        extra_fields.setdefault('phone_verified', True)
        extra_fields.setdefault('verification_status', 'verified')
        
        return self.create_user(phone, first_name, last_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = [
        ('user', 'مستخدم عادي'),
        ('volunteer', 'متطوع'),
        ('admin', 'مشرف'),
        ('super_admin', 'مدير نظام'),
    ]
    
    VERIFICATION_STATUS = [
        ('unverified', 'غير محقق'),
        ('pending', 'قيد الانتظار'),
        ('verified', 'تم التحقق'),
        ('rejected', 'مرفوض'),
    ]
    
    # Validator لرقم الهاتف
    phone_validator = RegexValidator(
        regex=r'^\+?[0-9]{8,15}$',
        message=_('رقم الهاتف يجب أن يتكون من 8 إلى 15 رقمًا، ويمكن أن يبدأ بـ +')
    )
    
    # المعلومات الأساسية
    from .fields import EncryptedCharField
    phone = EncryptedCharField(_('رقم الهاتف'), max_length=512, unique=True, db_index=True)
    # phone = encrypt(models.CharField(_('رقم الهاتف'), max_length=255, unique=True, db_index=True))
    first_name = models.CharField(_('الاسم الأول'), max_length=150, db_index=True)
    middle_name = models.CharField(_('الاسم الأوسط'), max_length=150, null=True, blank=True)
    last_name = models.CharField(_('اللقب'), max_length=150, db_index=True)
    email = models.EmailField(_('البريد الإلكتروني'), max_length=150, unique=True, blank=True, null=True)
    
    # موقع السكن
    home_governorate = models.ForeignKey(
        Governorate, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('محافظة السكن'), related_name='users'
    )
    home_district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('مديرية السكن'), related_name='users'
    )
    home_uzlah = models.ForeignKey(
        Uzlah, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('عزلة السكن'), related_name='users'
    )
    
    # نوع المستخدم والصلاحيات
    user_type = models.CharField(
        _('نوع المستخدم'), 
        max_length=20, 
        choices=USER_TYPE_CHOICES, 
        default='user',
        db_index=True
    )
    
    # حقل is_staff حقيقي (مطلوب لـ Django Admin)
    is_staff = models.BooleanField(
        _('موظف'),
        default=False,
        help_text=_('يحدد ما إذا كان المستخدم يمكنه الدخول إلى لوحة الإدارة')
    )
    
    # التحقق عبر OTP
    phone_verified = models.BooleanField(_('رقم الهاتف موثق'), default=False, db_index=True)
    otp_code = models.CharField(_('رمز التحقق'), max_length=6, null=True, blank=True)
    otp_expiry = models.DateTimeField(_('تاريخ انتهاء رمز التحقق'), null=True, blank=True)
    otp_attempts = models.IntegerField(_('محاولات التحقق'), default=0)
    last_otp_request = models.DateTimeField(_('آخر طلب رمز'), null=True, blank=True)
    
    # حالة التحقق الكامل (توثيق الهوية)
    verification_status = models.CharField(
        _('حالة التحقق من الهوية'), 
        max_length=20, 
        choices=VERIFICATION_STATUS, 
        default='unverified',
        db_index=True
    )
    
    # درجة الثقة
    trust_score = models.FloatField(_('درجة الثقة'), default=0.0)
    
    # حالة الحساب
    is_active = models.BooleanField(_('نشط'), default=True, db_index=True)
    date_joined = models.DateTimeField(_('تاريخ الانضمام'), default=timezone.now)
    last_activity = models.DateTimeField(_('آخر نشاط'), null=True, blank=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمين')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['phone', 'is_active']),
            models.Index(fields=['user_type', 'verification_status']),
        ]
    
    def __str__(self):
        """تمثيل نصي للمستخدم"""
        return f"{self.full_name} ({self.phone})"
    
    @property
    def full_name(self):
        """الاسم الكامل للمستخدم"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(part for part in parts if part)
    
    def is_admin(self):
        """التحقق مما إذا كان المستخدم مشرفاً"""
        return self.user_type in ['admin', 'super_admin']
    
    def is_volunteer_or_higher(self):
        """التحقق مما إذا كان المستخدم متطوعاً أو أعلى"""
        return self.user_type in ['volunteer', 'admin', 'super_admin']
    
    def can_access_admin(self):
        """التحقق من صلاحية الوصول إلى لوحة الإدارة"""
        return self.is_staff or self.user_type in ['admin', 'super_admin']
    
    def update_last_activity(self):
        """تحديث وقت آخر نشاط"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def increment_otp_attempts(self):
        """زيادة عدد محاولات OTP"""
        self.otp_attempts += 1
        self.save(update_fields=['otp_attempts'])
    
    def reset_otp_attempts(self):
        """إعادة تعيين محاولات OTP"""
        self.otp_attempts = 0
        self.save(update_fields=['otp_attempts'])