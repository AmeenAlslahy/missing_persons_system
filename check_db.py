import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def check_structure():
    tables = ['reports_person', 'reports_report']
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT COLUMN_NAME, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}'")
            rows = cursor.fetchall()
            print(f"\nColumns in {table}:")
            for row in rows:
                print(f" - {row[0]} (Nullable: {row[1]})")

if __name__ == "__main__":
    check_structure()
