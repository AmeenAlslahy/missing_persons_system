from django.apps import AppConfig


class MatchingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matching'
    verbose_name = 'نظام المطابقة'
    
    def ready(self):
        """استيراد الإشارات عند جاهزية التطبيق"""
        import matching.signals