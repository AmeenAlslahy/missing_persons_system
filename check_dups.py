import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from locations.models import Governorate

def check_duplicates():
    govs = Governorate.objects.all().order_by('id')
    name_map = {}
    
    for g in govs:
        key = g.name_ar or g.name
        if not key:
            continue
        
        # Normalize key
        key = key.strip()
        
        if key not in name_map:
            name_map[key] = []
        name_map[key].append(g)
        
    for key, gov_list in name_map.items():
        if len(gov_list) > 1:
            print(f"DUPLICATE FOUND for '{key}':")
            for g in gov_list:
                print(f"  - ID: {g.id}, name: {g.name}, name_ar: {g.name_ar}, dists: {g.districts.count()}")

if __name__ == "__main__":
    check_duplicates()
