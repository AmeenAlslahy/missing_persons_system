import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

try:
    user = User.objects.get(phone='713555262')
    user.is_staff = True
    user.is_superuser = True
    user.user_type = 'super_admin'
    user.set_password('Admin@2024')
    user.save()
    print('User promoted and password reset successfully')
except User.DoesNotExist:
    print('User not found')
except Exception as e:
    print(f'Error: {e}')
