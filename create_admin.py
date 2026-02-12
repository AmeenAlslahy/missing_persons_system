import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

try:
    if not User.objects.filter(email='admin@example.com').exists():
        User.objects.create_superuser(
            email='admin@example.com',
            full_name='Admin User',
            password='adminpassword123'
        )
        print("Superuser 'admin@example.com' created with password 'adminpassword123'.")
    else:
        print("Superuser already exists.")
except Exception as e:
    print(f"Error creating superuser: {e}")
