import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from locations.models import Governorate, District, Uzlah

def seed_sample_locations():
    data = {
        "أمانة العاصمة": ["صنعاء القديمة", "شعوب", "آزال", "الصافية", "السبعين", "الوحدة", "التحرير", "معين", "الثورة", "بني الحارث"],
        "صنعاء": ["صنعاء", "ارحب", "بني حشيش", "بني مطر", "خولان", "سنحان وبني بهلول", "صعفان", "مناخة", "نهم", "همدان"],
        "عدن": ["صيرة", "خور مكسر", "المعلا", "التواهي", "الشيخ عثمان", "المنصورة", "دار سعد", "البريقة"],
        "تعز": ["المظفر", "القاهرة", "صالة", "صبر الموادم", "المسراخ", "مشرعة وحدنان", "جبل حبشي", "المعافر", "المواسط", "الصلو", "الشمايتين", "الوازعية", "ذباب", "موزع", "مقبنة", "المخا", "التعزية", "شرعب الرونة", "شرعب السلام", "ماوية", "خدير", "حيفان", "سامع"],
        "الحديدة": ["مدينة الحديدة", "الحالي", "الحوك", "الميناء", "حيس", "الخوخة", "التحيتا", "الجراحي", "زبيد", "الدريهمي", "بيت الفقيه", "المنصورية", "السخنة", "المراوعة", "برع", "باجل", "الصليف", "الضحي", "الزيدية", "المغلاف", "القناوص", "الزهرة", "اللحية", "كمران"],
        "الضالع": ["الضالع", "الحشاء", "جحاف", "قعطبة", "الشعيب", "الحصين", "الأزارق", "جبن", "دمت"],
        "إب": ["إب", "جبلة", "ذي السفال", "السياني", "الرضمة", "السدة", "النادرة", "الشعر", "المخادر", "القفر", "حبيش", "حزم العدين", "العدين", "الفرع", "مذيخرة", "بعدان", "يريم", "السبرة"],
        "حضرموت": ["المكلا", "الشحر", "غيل باوزير", "غيل بن يمين", "الديس", "تريم", "سيئون", "شبام", "القطن", "دوعن", "حريضة", "رخية", "العبر"]
    }

    total_govs = 0
    total_districts = 0
    total_uzlahs = 0

    print("Seeding locations...")
    
    for gov_name, districts in data.items():
        gov = Governorate.objects.filter(name_ar=gov_name).first()
        if not gov:
            gov = Governorate.objects.filter(name=gov_name).first()
            
        if not gov:
             print(f"Governorate '{gov_name}' not found. Please ensure governorates exist first.")
             continue
             
        total_govs += 1
        
        for dist_name in districts:
            dist, created = District.objects.get_or_create(
                governorate=gov,
                name_ar=dist_name,
                defaults={'name': dist_name}
            )
            
            if created:
                total_districts += 1
                
            # Create a sample Uzlah for testing
            uzlah_name = f"عزلة {dist_name}"
            uzlah, u_created = Uzlah.objects.get_or_create(
                district=dist,
                name_ar=uzlah_name,
                defaults={'name': uzlah_name}
            )
            
            if u_created:
                total_uzlahs += 1
                
    print(f"Successfully seeded:")
    print(f"- {total_govs} Governorates checked")
    print(f"- {total_districts} New Districts added")
    print(f"- {total_uzlahs} New Uzlahs added")

if __name__ == "__main__":
    seed_sample_locations()
