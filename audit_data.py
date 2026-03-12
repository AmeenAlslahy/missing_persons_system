import os
import django
from django.db.models import Count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import Report, Person
from accounts.models import User
from matching.models import MatchResult
from analytics.models import DailyStats
from locations.models import Governorate

print("--- Database Count Audit ---")
print(f"Total Users: {User.objects.count()}")
print(f"Users by type: {list(User.objects.values('user_type').annotate(count=Count('id')))}")

print(f"\nTotal Reports: {Report.objects.count()}")
for r in Report.objects.all():
    print(f"- Report {r.report_code}: Gov={r.lost_governorate_id}, GovNameAr='{r.lost_governorate.name_ar if r.lost_governorate else 'NONE'}', Status={r.status}")

print(f"Reports by status: {list(Report.objects.values('status').annotate(count=Count('report_id')).order_by())}")
print(f"Reports by type: {list(Report.objects.values('report_type').annotate(count=Count('report_id')).order_by())}")

print(f"\nTotal Match Results: {MatchResult.objects.count()}")

print("\n--- Geography Check ---")
govs_with_null_name = Governorate.objects.filter(name_ar__isnull=True).count()
print(f"Governorates with NULL name_ar: {govs_with_null_name}")
if govs_with_null_name > 0:
    print("Example null govs:", list(Governorate.objects.filter(name_ar__isnull=True).values('id', 'name')[:5]))

reports_with_null_gov_name = Report.objects.filter(lost_governorate__isnull=False, lost_governorate__name_ar__isnull=True).count()
print(f"Reports with lost_governorate relation but NULL name_ar: {reports_with_null_gov_name}")

print("\n--- Analytics Sync Check ---")
today_stats = DailyStats.objects.filter(date=django.utils.timezone.now().date()).first()
if today_stats:
    print(f"DailyStats (Today) - status: {today_stats.total_reports} reports, {today_stats.total_users} users")
else:
    print("No DailyStats found for today.")
