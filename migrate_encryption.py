import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from reports.models import Report

from django.db import connection

def migrate():
    print("Starting migration...")
    
    with connection.cursor() as cursor:
        # Migrate Users
        cursor.execute("SELECT id, phone FROM accounts_user")
        users = cursor.fetchall()
        print(f"Migrating {len(users)} users...")
        for uid, raw_phone in users:
            try:
                # We have the raw_phone string/bytes from DB.
                # Now we just need to save it back through the model to encrypt it.
                user = User.objects.get(pk=uid)
                user.phone = raw_phone
                user.save()
                print(f"Migrated user ID {uid}")
            except Exception as e:
                print(f"Error on user {username}: {e}")
            
        # Migrate Reports
        cursor.execute("SELECT report_id, contact_phone, report_code FROM reports_report")
        reports = cursor.fetchall()
        print(f"Migrating {len(reports)} reports...")
        for rid, raw_phone, code in reports:
            try:
                report = Report.objects.get(report_id=rid)
                report.contact_phone = raw_phone
                report.save()
                print(f"Migrated report {code}")
            except Exception as e:
                print(f"Error on report {code}: {e}")

    print("Migration completed.")

if __name__ == "__main__":
    migrate()
