import sys
import os
import django

# إضافة مسار المشروع ومسار البيئة الافتراضية إذا لزم الأمر
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from locations.models import Governorate, District, Uzlah

def seed_locations():
    governorates = [
        'صنعاء', 'عدن', 'تعز', 'الحديدة', 'إب', 'ذمار', 'حضرموت', 
        'أبين', 'المهرة', 'الجوف', 'البيضاء', 'حجة', 'صعدة', 'ريمة', 
        'سقطرى', 'شبوة', 'مأرب', 'الضالع', 'عمران', 'المحويت'
    ]
    
    for gov_name in governorates:
        gov, created = Governorate.objects.get_or_create(name=gov_name)
        if created:
            print(f"تمت إضافة محافظة: {gov_name}")
        
    print("تم الانتهاء من بذر البيانات (Governorates).")

if __name__ == "__main__":
    seed_locations()
