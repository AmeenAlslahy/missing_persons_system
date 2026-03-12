import os
import django
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from reports.views import ReportViewSet

factory = RequestFactory()
request = factory.get('/api/reports/reports/', {
    'page': '1',
    'page_size': '10',
    'ordering': '-created_at',
    'search': '',
    'report_type': '',
    'status': ''
})

view = ReportViewSet.as_view({'get': 'list'})
try:
    response = view(request)
    print("STATUS_CODE:", response.status_code)
    try:
        data = response.data
        if 'results' in data and len(data['results']) > 0:
            print("KEYS RETURNED:", list(data['results'][0].keys()))
            print("FIRST RESULT:", data['results'][0])
        else:
            print("RESPONSE:", data)
    except Exception as e:
        print("ERROR PARSING RESPONSE:", str(e))
except Exception as e:
    import traceback
    traceback.print_exc()
