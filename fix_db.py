import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

with connection.cursor() as cursor:
    col = 'successful_reports_count'
    try:
        print(f"Dropping column {col}...")
        cursor.execute(f"ALTER TABLE accounts_user DROP COLUMN {col}")
        print(f"Column {col} dropped.")
    except Exception as e:
        print(f"Error dropping column: {e}")
