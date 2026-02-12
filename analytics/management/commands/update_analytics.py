from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.services import AnalyticsService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'تحديث الإحصائيات والتحليلات اليومية'

    def handle(self, *args, **options):
        self.stdout.write('🚀 بدء تحديث الإحصائيات اليومية...')
        
        try:
            service = AnalyticsService()
            
            # تحديث الإحصائيات اليومية
            stats = service.update_daily_stats()
            if stats:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ تم تحديث الإحصائيات لـ {stats.date}')
                )
            
            # تحديث مقاييس الأداء
            if service.update_performance_metrics():
                self.stdout.write(
                    self.style.SUCCESS('✅ تم تحديث مقاييس الأداء')
                )
            
            # تنظيف البيانات القديمة (كل 7 أيام)
            if timezone.now().weekday() == 0:  # كل إثنين
                cleaned = service.cleanup_old_data(days_to_keep=90)
                if cleaned:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ تم تنظيف {cleaned["deleted_stats"]} إحصائية و {cleaned["deleted_reports"]} تقرير قديم')
                    )
            
            self.stdout.write(self.style.SUCCESS('🎉 اكتمل تحديث الإحصائيات بنجاح'))
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الإحصائيات: {e}")
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ: {e}')
            )