import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from locations.models import Governorate, District
from reports.models import Report
from accounts.models import User

def merge_governorates():
    print(f"Total districts before merge: {District.objects.count()}")
    
    # 1. Group by Arabic name
    govs = Governorate.objects.all()
    name_map = {}
    
    for g in govs:
        key = g.name_ar or g.name
        if not key:
            continue
        key = key.strip()
        if key not in name_map:
            name_map[key] = []
        name_map[key].append(g)
        
    for key, gov_list in name_map.items():
        if len(gov_list) > 1:
            print(f"\n--- Checking {key} ---")
            
            # Find the "good" one (with code)
            good_gov = next((g for g in gov_list if g.code is not None), None)
            
            # Find the "old" one (without code, which was used in seed_locations)
            old_gov = next((g for g in gov_list if g.code is None), None)
            
            if good_gov and old_gov:
                print(f"Merging '{old_gov.name}' (ID {old_gov.id}) into '{good_gov.name}' (ID {good_gov.id})")
                
                # We will keep the OLD gov ID, but update its fields from the GOOD gov, 
                # because the OLD gov is likely referenced by existing DB foreign keys.
                
                # First, transfer any newly created relations from GOOD to OLD
                District.objects.filter(governorate=good_gov).update(governorate=old_gov)
                Report.objects.filter(lost_governorate=good_gov).update(lost_governorate=old_gov)
                from reports.models import Person
                Person.objects.filter(home_governorate=good_gov).update(home_governorate=old_gov)
                User.objects.filter(home_governorate=good_gov).update(home_governorate=old_gov)
                
                # Clear the unique fields on the good_gov so we can save them on old_gov
                good_gov.name = good_gov.name + "_DUPE_" + str(good_gov.id)
                if good_gov.code:
                    good_gov.code = good_gov.code + "_D"
                good_gov.save()
                
                # Copy fields
                old_gov.name = good_gov.name.replace("_DUPE_" + str(good_gov.id), "")
                old_gov.name_ar = good_gov.name_ar
                old_gov.name_en = good_gov.name_en
                old_gov.code = good_gov.code.replace("_D", "") if good_gov.code else None
                old_gov.save()
                
                # Delete the GOOD gov (which is now empty and duplicate)
                good_gov.delete()
                print(f"Merged and deleted duplicate {good_gov.id}")
            else:
                print(f"Cannot automatically merge {key} - condition not met.")

if __name__ == "__main__":
    merge_governorates()
