from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from .models import User, VolunteerProfile


@receiver(post_save, sender=User)
def create_volunteer_profile(sender, instance, created, **kwargs):
    """
    إنشاء ملف متطوع تلقائيًا عند تحويل المستخدم لمتطوع
    """
    if not created and instance.user_role in ['volunteer', 'admin', 'super_admin']:
        VolunteerProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def log_user_creation(sender, instance, created, **kwargs):
    """تسجيل إنشاء مستخدم جديد في سجل التدقيق"""
    if created:
        instance.audit_logs.create(
            action_type='USER_CREATED',
            action_details=_('تم إنشاء حساب جديد')
        )