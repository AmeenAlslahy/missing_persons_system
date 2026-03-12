import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def drop_stray_columns():
    with connection.cursor() as cursor:
        print("Dropping stray columns from reports_report...")
        columns = ['governorate', 'district', 'uzlah']
        for col in columns:
            try:
                # Check if column exists first
                cursor.execute(f"IF COL_LENGTH('reports_report', '{col}') IS NOT NULL ALTER TABLE reports_report DROP COLUMN {col}")
                print(f" - {col} dropped")
            except Exception as e:
                print(f" - Error dropping {col}: {e}")

if __name__ == "__main__":
    drop_stray_columns()
