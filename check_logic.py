import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import Report
from matching.models import MatchResult
from accounts.models import User
from django.utils import timezone

print("Checking for illogical operations...")

# Check reports with future dates
future_reports = Report.objects.filter(last_seen_date__gt=timezone.now().date())
if future_reports.exists():
    print(f"⚠️ Found {future_reports.count()} reports with future dates:")
    for r in future_reports:
        print(f"  Report {r.report_code}: {r.last_seen_date}")

# Check resolved reports that are still active
resolved_active = Report.objects.filter(status='resolved', resolved_at__isnull=True)
if resolved_active.exists():
    print(f"⚠️ Found {resolved_active.count()} resolved reports without resolution date:")
    for r in resolved_active:
        print(f"  Report {r.report_code}: status={r.status}, resolved_at={r.resolved_at}")

# Check matches with low similarity but accepted
accepted_low_similarity = MatchResult.objects.filter(match_status='accepted', similarity_score__lt=0.5)
if accepted_low_similarity.exists():
    print(f"⚠️ Found {accepted_low_similarity.count()} accepted matches with low similarity (<50%):")
    for m in accepted_low_similarity:
        print(f"  Match {m.id}: similarity={m.similarity_score}, status={m.match_status}")

# Check users with negative trust scores
negative_trust = User.objects.filter(trust_score__lt=0)
if negative_trust.exists():
    print(f"⚠️ Found {negative_trust.count()} users with negative trust scores:")
    for u in negative_trust:
        print(f"  User {u.email}: trust_score={u.trust_score}")

# Check reports with age > 150
old_age_reports = Report.objects.filter(age__gt=150)
if old_age_reports.exists():
    print(f"⚠️ Found {old_age_reports.count()} reports with unrealistic age (>150):")
    for r in old_age_reports:
        print(f"  Report {r.report_code}: age={r.age}")

print("Logic check completed.")
