from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


def apply_age_filter(queryset, min_age=None, max_age=None, date_field='last_seen_date'):
    """
    تطبيق فلتر العمر على QuerySet
    """
    today = date.today()
    
    if min_age is not None:
        try:
            min_age = int(min_age)
            min_birth_date = today - relativedelta(years=min_age)
            queryset = queryset.filter(person__date_of_birth__lte=min_birth_date)
        except (ValueError, TypeError) as e:
            logger.error(f"Error applying min_age filter: {e}")
    
    if max_age is not None:
        try:
            max_age = int(max_age)
            max_birth_date = today - relativedelta(years=max_age)
            queryset = queryset.filter(person__date_of_birth__gte=max_birth_date)
        except (ValueError, TypeError) as e:
            logger.error(f"Error applying max_age filter: {e}")
    
    return queryset


def obfuscate_phone(phone, visible_digits=4):
    """
    إخفاء رقم الهاتف مع إظهار آخر digits
    """
    if not phone or len(phone) <= visible_digits:
        return phone
    
    phone_str = str(phone)
    return '*' * (len(phone_str) - visible_digits) + phone_str[-visible_digits:]


def calculate_age(birth_date, reference_date=None):
    """
    حساب العمر بدقة
    """
    if not birth_date:
        return None
    
    if reference_date is None:
        reference_date = date.today()
    
    age = reference_date.year - birth_date.year
    
    # تصحيح إذا لم يأتِ عيد الميلاد بعد
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    return age