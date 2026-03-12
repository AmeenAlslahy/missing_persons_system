import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.views import ReportStatisticsView
from rest_framework.test import APIRequestFactory
from accounts.models import User

# Mock a regular user
user = User.objects.filter(user_type='user').first()
if not user:
    # Fallback to any user
    user = User.objects.first()

factory = APIRequestFactory()
request = factory.get('/api/reports/statistics/')
request.user = user

view = ReportStatisticsView.as_view()
response = view(request)

print(f"Status Code: {response.status_code}")
print("Response Data:")
print(json.dumps(response.data, indent=2, ensure_ascii=False))
