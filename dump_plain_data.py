import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from reports.models import Report

def dump():
    data = {
        'users': [],
        'reports': []
    }
    
    print("Dumping Users...")
    for user in User.objects.all():
        data['users'].append({
            'id': str(user.id),
            'phone': user.phone
        })
        
    print("Dumping Reports...")
    for report in Report.objects.all():
        data['reports'].append({
            'report_id': str(report.report_id),
            'contact_phone': report.contact_phone
        })
        
    with open('plain_data_dump.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print("Dump completed to plain_data_dump.json")

if __name__ == "__main__":
    dump()
