import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def reset_apps():
    # Tables in order of dependency (drop children first)
    tables_to_drop = [
        'notifications_notification',
        'matching_matchingauditlog',
        'matching_matchresult',
        'reports_reportimage',
        'reports_report',
        'reports_person'
    ]
    
    apps_to_reset = ['reports', 'matching', 'notifications']
    
    with connection.cursor() as cursor:
        print("Dropping tables...")
        for table in tables_to_drop:
            try:
                # SQL Server syntax to drop if exists
                cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table}")
                print(f" - {table} dropped (if it existed)")
            except Exception as e:
                print(f" - Error dropping {table}: {e}")
        
        print("\nDeleting migration history for apps...")
        for app in apps_to_reset:
            try:
                cursor.execute(f"DELETE FROM django_migrations WHERE app = '{app}'")
                print(f" - Migration history cleared for '{app}'.")
            except Exception as e:
                print(f" - Error clearing migration history for '{app}': {e}")

if __name__ == "__main__":
    reset_apps()
