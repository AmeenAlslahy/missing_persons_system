import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import Report
from django.db.models import Count

total = Report.objects.count()
print(f"Total reports: {total}")

status_counts = Report.objects.values('status').annotate(count=Count('report_id')).order_by()
for entry in status_counts:
    print(f"Status: {entry['status']}, Count: {entry['count']}")
