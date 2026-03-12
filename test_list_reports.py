import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.serializers import ReportSerializer
from reports.models import Report
from accounts.models import User
from django.test import RequestFactory

def test_list_reports():
    # Setup
    user = User.objects.filter(user_type='super_admin').first()
    if not user:
        print("No superuser found for testing.")
        return

    # Use RequestFactory to provide context to serializer
    factory = RequestFactory()
    request = factory.get('/api/reports/reports/')
    request.user = user

    reports = Report.objects.all()[:5]
    print(f"Testing serializer on {reports.count()} reports...")
    
    try:
        serializer = ReportSerializer(reports, many=True, context={'request': request})
        data = serializer.data
        print("SUCCESS: Serialized data successfully.")
        # print(json.dumps(data[0] if data else {}, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"FAILED: Serializer crashed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_list_reports()
