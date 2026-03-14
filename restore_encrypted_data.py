import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from reports.models import Report

def restore():
    if not os.path.exists('plain_data_dump.json'):
        print("Error: plain_data_dump.json not found!")
        return
        
    with open('plain_data_dump.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print("Restoring Users...")
    for user_data in data['users']:
        uid = user_data['id']
        phone = user_data['phone']
        try:
            # IMPORTANT: defer('phone') avoids triggering BadSignature on existing plain text
            user = User.objects.defer('phone').get(id=uid)
            user.phone = phone if phone else ""
            user.save()
            print(f"Restored and encrypted user ID {uid}")
        except Exception as e:
            print(f"Error on user ID {uid}: {e}")
            
    print("Restoring Reports...")
    for report_data in data['reports']:
        rid = report_data['report_id']
        phone = report_data['contact_phone']
        try:
            # IMPORTANT: defer('contact_phone') avoids BadSignature
            report = Report.objects.defer('contact_phone').get(report_id=rid)
            report.contact_phone = phone if phone else ""
            report.save()
            print(f"Restored and encrypted report ID {rid}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error on report ID {rid}: {e}")
            
    print("Restoration and encryption completed.")

if __name__ == "__main__":
    restore()
