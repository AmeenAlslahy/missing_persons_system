import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def reset_analytics():
    tables_to_drop = [
        'analytics_analyticsreport_allowed_users',
        'analytics_analyticsreport',
        'analytics_dailystats',
        'analytics_performancemetric',
        'analytics_dashboardwidget',
        'analytics_requestlog'
    ]
    
    with connection.cursor() as cursor:
        print("Dropping analytics tables...")
        for table in tables_to_drop:
            try:
                # Use DROP TABLE IF EXISTS or just try/except
                # In SQL Server: IF OBJECT_ID('table', 'U') IS NOT NULL DROP TABLE table
                cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table}")
                print(f" - {table} dropped (if it existed)")
            except Exception as e:
                print(f" - Error dropping {table}: {e}")
        
        print("\nDeleting migration history for 'analytics' app...")
        try:
            cursor.execute("DELETE FROM django_migrations WHERE app = 'analytics'")
            print(" - Migration history cleared.")
        except Exception as e:
            print(f" - Error clearing migration history: {e}")

if __name__ == "__main__":
    reset_analytics()
