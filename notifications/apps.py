from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'نظام الإشعارات'
    
    def ready(self):
        """استيراد الإشارات عند جاهزية التطبيق"""
        import notifications.signals