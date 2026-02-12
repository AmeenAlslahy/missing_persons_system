from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'الإحصائيات والتحليلات'
    
    def ready(self):
        """استيراد الإشارات عند جاهزية التطبيق"""
        import analytics.signals