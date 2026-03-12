import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.views import ReportViewSet
from rest_framework.test import APIRequestFactory
from accounts.models import User

# Mock a staff user
user = User.objects.filter(user_type__in=['admin', 'super_admin']).first()
if not user:
    user = User.objects.first()

factory = APIRequestFactory()
request = factory.get('/api/reports/reports/')
request.user = user

view = ReportViewSet.as_view({'get': 'list'})
try:
    response = view(request)
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print("Response Error Data:")
        print(response.data)
    else:
        print("Response Data (First result):")
        if response.data.get('results'):
            print(json.dumps(response.data['results'][0], indent=2, ensure_ascii=False))
        else:
            print("No results found.")
except Exception as e:
    print(f"Exception occurred: {str(e)}")
    import traceback
    traceback.print_exc()
