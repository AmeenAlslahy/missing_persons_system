import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import Report
from accounts.models import User
from django.test import RequestFactory
from reports.views import ReportViewSet
from rest_framework import status

def test_reject_report():
    # Setup
    admin_user = User.objects.filter(user_type='super_admin').first()
    if not admin_user:
        print("No superuser found for testing.")
        return

    report = Report.objects.filter(status='pending').first()
    if not report:
        print("No pending report found for testing.")
        # Create a report if none exists
        from reports.models import Person, Governorate, District
        person = Person.objects.create(first_name="Test", last_name="Rej", gender="M")
        gov = Governorate.objects.first()
        dist = District.objects.filter(governorate=gov).first()
        report = Report.objects.create(
            user=admin_user,
            person=person,
            report_type='missing',
            lost_governorate=gov,
            lost_district=dist,
            last_seen_date='2023-10-01',
            health_at_loss='Good',
            contact_phone='123456',
            status='pending'
        )

    print(f"Testing rejection on report {report.report_id} ({report.report_code})...")
    
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=admin_user)
    
    url = f'/api/reports/reports/{report.report_id}/review/'
    data = {
        'action': 'reject',
        'rejection_reason': 'Invalid data provided'
    }
    
    try:
        response = client.post(url, data=data, format='json')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data}")
    except Exception as e:

        print(f"CRASH: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reject_report()
