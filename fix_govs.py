import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from locations.models import Governorate

governorates_data = [
    {'code': '01', 'name': 'Amanat Al Asimah', 'name_ar': 'أمانة العاصمة'},
    {'code': '02', 'name': 'Aden', 'name_ar': 'عدن'},
    {'code': '03', 'name': 'Taizz', 'name_ar': 'تعز'},
    {'code': '04', 'name': 'Al Hudaydah', 'name_ar': 'الحديدة'},
    {'code': '05', 'name': 'Ibb', 'name_ar': 'إب'},
    {'code': '06', 'name': 'Abyan', 'name_ar': 'أبين'},
    {'code': '07', 'name': 'Al Bayda', 'name_ar': 'البيضاء'},
    {'code': '08', 'name': 'Al Jawf', 'name_ar': 'الجوف'},
    {'code': '09', 'name': 'Hadramaut', 'name_ar': 'حضرموت'},
    {'code': '10', 'name': 'Hajjah', 'name_ar': 'حجة'},
    {'code': '11', 'name': 'Al Mahrah', 'name_ar': 'المهرة'},
    {'code': '12', 'name': 'Al Mahwit', 'name_ar': 'المحويت'},
    {'code': '13', 'name': 'Marib', 'name_ar': 'مأرب'},
    {'code': '14', 'name': 'Saada', 'name_ar': 'صعدة'},
    {'code': '15', 'name': 'Sana\'a', 'name_ar': 'صنعاء'},
    {'code': '16', 'name': 'Shabwah', 'name_ar': 'شبوة'},
    {'code': '17', 'name': 'Amran', 'name_ar': 'عمران'},
    {'code': '18', 'name': 'Ad Dali', 'name_ar': 'الضالع'},
    {'code': '19', 'name': 'Raymah', 'name_ar': 'ريمة'},
    {'code': '20', 'name': 'Socotra', 'name_ar': 'سقطرى'},
    {'code': '21', 'name': 'Dhamar', 'name_ar': 'ذمار'},
    {'code': '22', 'name': 'Lahij', 'name_ar': 'لحج'},
]

for data in governorates_data:
    # Try to find by code, english name, or arabic name in ANY field
    gov = Governorate.objects.filter(code=data['code']).first()
    if not gov:
        gov = Governorate.objects.filter(name=data['name_ar']).first()
    if not gov:
        gov = Governorate.objects.filter(name_ar=data['name_ar']).first()
    if not gov:
        gov = Governorate.objects.filter(name=data['name']).first()
    
    if gov:
        print(f"Updating Gov {gov.id}: {gov.name} -> {data['name_ar']}")
        gov.code = data['code']
        gov.name = data['name']
        gov.name_ar = data['name_ar']
        gov.save()
    else:
        print(f"Creating new Gov: {data['name_ar']}")
        Governorate.objects.create(**data)
