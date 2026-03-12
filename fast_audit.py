import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from reports.models import Report
from locations.models import Governorate

print("--- Reports Audit ---")
for r in Report.objects.all():
    gov = r.lost_governorate
    print(f"Report: {r.report_code}, GovID: {r.lost_governorate_id}, GovName: {gov.name if gov else 'N/A'}, GovNameAr: {gov.name_ar if gov else 'N/A'}")

print("\n--- Governorate Audit (NULL name_ar) ---")
null_govs = Governorate.objects.filter(name_ar__isnull=True)
print(f"Count: {null_govs.count()}")
for g in null_govs[:10]:
    print(f"ID: {g.id}, Name: {g.name}")
