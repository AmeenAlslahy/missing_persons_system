import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def execute_sql(sql_list):
    with connection.cursor() as cursor:
        for sql in sql_list:
            try:
                print(f"Executing: {sql}")
                cursor.execute(sql)
                print("Success")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    sql_commands = [
        # DROP problematic columns from accounts_user
        "ALTER TABLE accounts_user DROP COLUMN governorate",
        "ALTER TABLE accounts_user DROP COLUMN district",
        "ALTER TABLE accounts_user DROP COLUMN uzlah",
        "ALTER TABLE accounts_user DROP COLUMN trust_score",
        "ALTER TABLE accounts_user DROP COLUMN verification_status",
        # "user_role" is already missing according to check_db.py
        
        # DROP problematic columns from reports_report
        "ALTER TABLE reports_report DROP COLUMN governorate",
        "ALTER TABLE reports_report DROP COLUMN district",
        "ALTER TABLE reports_report DROP COLUMN uzlah",
    ]
    execute_sql(sql_commands)
