import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

phone = '713555262'
user = User.objects.filter(phone=phone).first()

if user:
    print(f"USER_FOUND: {user.phone}")
    print(f"USER_TYPE: {user.user_type}")
    print(f"IS_STAFF: {user.is_staff}")
else:
    print("USER_NOT_FOUND")
