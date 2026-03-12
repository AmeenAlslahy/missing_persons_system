import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

phone = '713555262'
user = User.objects.filter(phone=phone).first()

if user:
    user.user_type = 'super_admin'
    user.save()
    print(f"SUCCESS: User {user.phone} upgraded to super_admin")
else:
    print("ERROR: User not found")
