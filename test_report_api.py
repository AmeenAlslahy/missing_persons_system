from reports.views import ReportViewSet
from rest_framework.test import APIRequestFactory
import traceback

factory = APIRequestFactory()
request = factory.get('/api/reports/reports/')
view = ReportViewSet.as_view({'get': 'list'})

try:
    response = view(request)
    print('STATUS_CODE:', response.status_code)
    try:
        response.render()
        print('RESPONSE_CONTENT:', response.content.decode('utf-8'))
    except Exception as e:
        print('RENDER_ERROR:', e)
except Exception as e:
    traceback.print_exc()
