from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from locations.models import Governorate, District, Uzlah

class CustomUserManager(BaseUserManager):
    def create_user(self, phone, first_name, last_name, password=None, **extra_fields):
        if not phone:
            raise ValueError(_('يجب إدخال رقم الهاتف'))
        if not first_name or not last_name:
            raise ValueError(_('يجب إدخال الاسم الأول واللقب'))
            
        user = self.model(phone=phone, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'super_admin')
        
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
    
    # المعلومات الأساسية
    phone = models.CharField(_('رقم الهاتف'), max_length=20, unique=True)
    first_name = models.CharField(_('الاسم الأول'), max_length=150)
    middle_name = models.CharField(_('الاسم الأوسط'), max_length=150, null=True, blank=True)
    last_name = models.CharField(_('اللقب'), max_length=150)
    email = models.EmailField(_('البريد الإلكتروني'), null=True, blank=True)
    
    # موقع السكن (قد يتغير لكن نادراً)
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
    user_type = models.CharField(_('نوع المستخدم'), max_length=20, choices=USER_TYPE_CHOICES, default='user')
    
    # التحقق عبر OTP
    phone_verified = models.BooleanField(_('رقم الهاتف موثق'), default=False)
    otp_code = models.CharField(_('رمز التحقق'), max_length=6, null=True, blank=True)
    otp_expiry = models.DateTimeField(_('تاريخ انتهاء رمز التحقق'), null=True, blank=True)
    otp_attempts = models.IntegerField(_('محاولات التحقق'), default=0)
    last_otp_request = models.DateTimeField(_('آخر طلب رمز'), null=True, blank=True)
    
    # حالة التحقق الكامل (توثيق الهوية)
    verification_status = models.CharField(
        _('حالة التحقق من الهوية'), max_length=20, choices=VERIFICATION_STATUS, default='unverified'
    )
    
    # درجة الثقة
    trust_score = models.FloatField(_('درجة الثقة'), default=0.0)
    
    # حالة الحساب
    is_active = models.BooleanField(_('نشط'), default=True)
    date_joined = models.DateTimeField(_('تاريخ الانضمام'), default=timezone.now)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمين')
    
    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)
    
    @property
    def is_staff(self):
        return self.user_type in ['admin', 'super_admin']
    
    @property
    def is_superuser(self):
        return self.user_type == 'super_admin'
    
    def __str__(self):
        return f"{self.full_name} ({self.phone})"