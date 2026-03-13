# import os
# from celery import Celery

# # تحديد ملف الإعدادات الافتراضي لـ Django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# # إنشاء تطبيق Celery باسم المشروع
# app = Celery('missing_persons_system')

# # قراءة الإعدادات من ملف settings.py باستخدام بادئة CELERY_
# app.config_from_object('django.conf:settings', namespace='CELERY')

# # البحث التلقائي عن ملفات tasks.py في جميع تطبيقات Django (مثل reports, notifications)
# app.autodiscover_tasks()

# @app.task(bind=True, ignore_result=True)
# def debug_task(self):
#     print(f'Request: {self.request!r}')