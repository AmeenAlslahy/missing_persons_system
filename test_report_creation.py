import os
import django
from django.utils import timezone
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.serializers import ReportSerializer
from locations.models import Governorate, District, Uzlah
from accounts.models import User
from django.test import RequestFactory

def test_create_report():
    # Setup
    user = User.objects.filter(user_type='super_admin').first()
    if not user:
        print("No superuser found for testing.")
        return

    gov = Governorate.objects.first()
    dist = District.objects.filter(governorate=gov).first()
    uzlah = Uzlah.objects.filter(district=dist).first()

    if not gov or not dist:
        print("No governorate or district found for testing.")
        return

    data = {
        'report_type': 'missing',
        'person_first_name': 'Test',
        'person_middle_name': 'User',
        'person_last_name': 'Alpha',
        'person_gender': 'M',
        'person_date_of_birth': '2010-01-01',
        'person_blood_type': 'A+',
        'lost_governorate': gov.id,
        'lost_district': dist.id,
        'lost_uzlah': uzlah.id if uzlah else None,
        'lost_location_details': 'Near the park',
        'last_seen_date': '2023-10-01',
        'health_at_loss': 'Good',
        'importance': 'medium',
        'contact_phone': '777123456',
        'status': 'pending'
    }

    # Use RequestFactory to provide context to serializer
    factory = RequestFactory()
    request = factory.post('/api/reports/reports/')
    request.user = user

    serializer = ReportSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        report = serializer.save(user=user)
        print(f"SUCCESS: Report created with code {report.report_code}")
        print(f"Person linked: {report.person.full_name}")
    else:
        print("FAILED: Serializer errors:")
        print(serializer.errors)

if __name__ == "__main__":
    test_create_report()
