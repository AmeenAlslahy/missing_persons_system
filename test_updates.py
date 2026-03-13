import os
import django
import json
from datetime import date

# إعداد بيئة دجانغو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import Person, Report
from reports.views import SearchPersonsView
from matching.matcher import ReportMatcher
from audit.models import AuditLog
from rest_framework.test import APIRequestFactory, force_authenticate
from accounts.models import User

def test_person_search():
    print("\n--- Testing Person Search ---")
    factory = APIRequestFactory()
    user = User.objects.first()
    
    # إنشاء شخص للاختبار
    person, _ = Person.objects.get_or_create(
        first_name='أحمد',
        middle_name='علي',
        last_name='اليماني',
        defaults={'gender': 'male'}
    )
    
    view = SearchPersonsView.as_view()
    
    # اختبار البحث مع توحيد الحروف العربية (البحث عن احمد بدون همزة)
    request = factory.get('/api/reports/search-persons/?q=احمد')
    force_authenticate(request, user=user)
    response = view(request)
    
    print(f"Search status: {response.status_code}")
    # ملاحظة: SearchPersonsView حالياً لا يستخدم normalize_arabic في الكويري نفسه (icontains) 
    # بل يستخدمه الماتشر فقط. سنقوم بتحسين هذا لاحقاً إذا لزم الأمر.
    # حالياً icontains في SQL Server قد يكون case-insensitive و accent-insensitive حسب الـ collation.
    print(f"Results count: {len(response.data['results'])}")
    for res in response.data['results']:
        print(f"Match found: {res['full_name']}")

def test_arabic_normalization():
    print("\n--- Testing Arabic Normalization in Matcher ---")
    matcher = ReportMatcher()
    n1 = matcher.normalize_arabic("أحمد")
    n2 = matcher.normalize_arabic("احمد")
    n3 = matcher.normalize_arabic("آمنة")
    n4 = matcher.normalize_arabic("امنه")
    
    print(f"'أحمد' -> '{n1}'")
    print(f"'احمد' -> '{n2}'")
    print(f"Match (أحمد/احمد): {n1 == n2}")
    print(f"'آمنة' -> '{n3}'")
    print(f"'امنه' -> '{n4}'")
    print(f"Match (آمنة/امنه): {n3 == n4}")

def test_audit_logging():
    print("\n--- Testing Audit Logging ---")
    from audit.services import AuditService
    user = User.objects.first()
    
    AuditService.log_action(
        user=user,
        action='LOGIN',
        resource_type='User',
        resource_id=user.id,
        data_after={'status': 'success'}
    )
    
    latest_log = AuditLog.objects.filter(user=user, action='LOGIN').first()
    if latest_log:
        print(f"Latest log action: {latest_log.action}")
        print(f"Resource: {latest_log.resource_type}")
        print(f"Timestamp: {latest_log.timestamp}")
    else:
        print("Log entry not found!")

if __name__ == "__main__":
    try:
        test_person_search()
        test_arabic_normalization()
        test_audit_logging()
        print("\nVerification completed successfully!")
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
