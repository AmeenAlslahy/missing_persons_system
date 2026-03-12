from django.core.management.base import BaseCommand
from locations.models import Governorate, District, Uzlah


class Command(BaseCommand):
    help = 'إضافة بيانات افتراضية للمحافظات والمديريات والعزل'

    def handle(self, *args, **kwargs):
        self.stdout.write('جاري إضافة البيانات الافتراضية...')
        
        # قائمة المحافظات اليمنية المتكاملة
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
        
        for gov_data in governorates_data:
            # محاولة البحث بالكود أولاً، ثم بالاسم، ثم بالاسم العربي
            gov = Governorate.objects.filter(code=gov_data['code']).first()
            if not gov:
                gov = Governorate.objects.filter(name=gov_data['name_ar']).first()
            if not gov:
                gov = Governorate.objects.filter(name=gov_data['name']).first()
            
            if gov:
                gov.code = gov_data['code']
                gov.name = gov_data['name']
                gov.name_ar = gov_data['name_ar']
                gov.save()
                self.stdout.write(f'تم تحديث محافظة: {gov.name_ar}')
            else:
                gov = Governorate.objects.create(**gov_data)
                self.stdout.write(f'تم إضافة محافظة: {gov.name_ar}')
        
        self.stdout.write(self.style.SUCCESS('تم إضافة البيانات الافتراضية بنجاح'))