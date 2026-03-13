from django.utils import timezone
from datetime import timedelta
import logging
from .models import DailyStats, PerformanceMetric
from reports.models import Report
from matching.models import MatchResult
from accounts.models import User
from django.db.models import Count, Q, Avg

logger = logging.getLogger(__name__)


class AnalyticsService:
    """خدمة التحليلات والإحصائيات"""
    
    def update_report_stats(self, report, created=False):
        """
        تحديث الإحصائيات عند تغيير تقرير
        """
        try:
            # تحديث إحصائيات اليوم
            self.update_daily_stats()
            
            # إذا تم حل البلاغ، نحدث مقاييس الأداء أيضاً
            if report.status == 'resolved':
                self.update_performance_metrics()
                
            return True
        except Exception as e:
            logger.error(f"خطأ في تحديث إحصائيات التقرير: {e}")
            return False

    def update_all_stats(self):
        """
        تحديث جميع الإحصائيات بشكل متكامل
        """
        today = timezone.now().date()
        
        # تحديث الإحصائيات اليومية
        daily_stats = self.update_daily_stats(today)
        
        # تحديث مقاييس الأداء
        self.update_performance_metrics()
        
        # تحديث إحصائيات المطابقة
        self._update_matching_stats()
        
        return daily_stats

    def _update_matching_stats(self):
        """
        تحديث إحصائيات المطابقة
        """
        from matching.models import MatchResult
        from django.db.models import Count, Avg
        from django.core.cache import cache
        
        stats = {
            'total_matches': MatchResult.objects.count(),
            'accepted_matches': MatchResult.objects.filter(match_status='accepted').count(),
            'pending_matches': MatchResult.objects.filter(match_status='pending').count(),
            'rejected_matches': MatchResult.objects.filter(match_status='rejected').count(),
            'avg_similarity': MatchResult.objects.aggregate(Avg('similarity_score'))['similarity_score__avg'] or 0,
        }
        
        # تخزين في كاش للوصول السريع
        cache.set('matching_stats', stats, timeout=3600)
        
        return stats

    def update_daily_stats(self, date=None):
        """
        تحديث الإحصائيات اليومية
        """
        try:
            if not date:
                date = timezone.now().date()
            
            stats, created = DailyStats.objects.get_or_create(date=date)
            stats.calculate_stats()
            
            logger.info(f"تم تحديث الإحصائيات اليومية لـ {date}")
            return stats
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الإحصائيات اليومية: {e}")
            return None
    
    def update_performance_metrics(self):
        """
        تحديث مقاييس الأداء
        """
        try:
            metrics_to_update = {
                'match_success_rate': self._calculate_match_success_rate(),
                'resolution_rate': self._calculate_resolution_rate(),
            }
            
            for metric_name, value in metrics_to_update.items():
                metric, created = PerformanceMetric.objects.get_or_create(
                    metric_name=metric_name,
                    defaults={
                        'metric_description': self._get_metric_description(metric_name),
                        'current_value': value,
                        'category': self._get_metric_category(metric_name),
                        'unit': '%',
                        'target_value': 90.0,
                    }
                )
                
                if not created:
                    metric.current_value = value
                    metric.save(update_fields=['current_value', 'last_updated'])
            
            logger.info("تم تحديث مقاييس الأداء")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحديث مقاييس الأداء: {e}")
            return False
    
    def _calculate_match_success_rate(self):
        """حساب معدل نجاح المطابقة"""
        accepted = MatchResult.objects.filter(match_status='accepted').count()
        reviewed = MatchResult.objects.filter(
            match_status__in=['accepted', 'rejected', 'false_positive']
        ).count()
        
        if reviewed > 0:
            return (accepted / reviewed) * 100
        return 0.0
    
    def _calculate_resolution_rate(self):
        """حساب معدل حل البلاغات"""
        resolved = Report.objects.filter(status='resolved').count()
        total = Report.objects.count()
        
        if total > 0:
            return (resolved / total) * 100
        return 0.0
    
    def _get_metric_description(self, metric_name):
        """الحصول على وصف المقياس"""
        descriptions = {
            'match_success_rate': 'نسبة المطابقات المقبولة من إجمالي المطابقات المراجعة',
            'resolution_rate': 'نسبة البلاغات التي تم حلها من إجمالي البلاغات',
        }
        return descriptions.get(metric_name, 'مقياس أداء النظام')
    
    def _get_metric_category(self, metric_name):
        """الحصول على فئة المقياس"""
        categories = {
            'match_success_rate': 'matching',
            'resolution_rate': 'report',
        }
        return categories.get(metric_name, 'system')
    
    def generate_performance_report(self, start_date, end_date):
        """
        توليد تقرير أداء للفترة المحددة
        """
        try:
            # الحصول على الإحصائيات اليومية
            daily_stats = DailyStats.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')
            
            if not daily_stats:
                return {
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'days': (end_date - start_date).days + 1
                    },
                    'summary': {},
                    'trends': {},
                    'insights': ["لا توجد بيانات للفترة المحددة"]
                }
            
            # تحليل البيانات
            report_data = {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': (end_date - start_date).days + 1
                },
                'summary': {
                    'total_reports': sum(stat.new_reports for stat in daily_stats),
                    'total_matches': sum(stat.new_matches for stat in daily_stats),
                    'total_users': sum(stat.new_users for stat in daily_stats),
                    'avg_match_rate': sum(stat.match_success_rate for stat in daily_stats) / len(daily_stats) if daily_stats else 0,
                },
                'trends': {
                    'reports': [stat.new_reports for stat in daily_stats],
                    'matches': [stat.new_matches for stat in daily_stats],
                    'users': [stat.new_users for stat in daily_stats],
                    'dates': [stat.date.isoformat() for stat in daily_stats],
                },
                'insights': self._generate_performance_insights(daily_stats),
            }
            
            return report_data
            
        except Exception as e:
            logger.error(f"خطأ في توليد تقرير الأداء: {e}")
            return None
    
    def _generate_performance_insights(self, daily_stats):
        """توليد رؤى من الإحصائيات"""
        insights = []
        
        if not daily_stats:
            return ["لا توجد بيانات للفترة المحددة"]
        
        # تحليل الاتجاهات
        reports_trend = self.analyze_trend([stat.new_reports for stat in daily_stats])
        matches_trend = self.analyze_trend([stat.new_matches for stat in daily_stats])
        users_trend = self.analyze_trend([stat.new_users for stat in daily_stats])
        
        if reports_trend == 'increasing':
            insights.append("عدد البلاغات الجديدة في تزايد مستمر")
        elif reports_trend == 'decreasing':
            insights.append("عدد البلاغات الجديدة في تناقص")
        
        if matches_trend == 'increasing':
            insights.append("عدد المطابقات المكتشفة في تزايد")
        
        if users_trend == 'increasing':
            insights.append("عدد المستخدمين الجدد في تزايد")
        
        # تحليل معدل النجاح
        success_rates = [stat.match_success_rate for stat in daily_stats if stat.match_success_rate > 0]
        if success_rates:
            avg_success = sum(success_rates) / len(success_rates)
            if avg_success < 70:
                insights.append(f"معدل نجاح المطابقة منخفض ({avg_success:.1f}%)")
            elif avg_success > 90:
                insights.append(f"معدل نجاح المطابقة ممتاز ({avg_success:.1f}%)")
        
        return insights if insights else ["الأداء مستقر خلال الفترة المحددة"]
    
    def analyze_trend(self, data):
        """تحليل اتجاه البيانات"""
        if len(data) < 2:
            return 'stable'
        
        # حساب متوسط التغير
        changes = [data[i] - data[i-1] for i in range(1, len(data))]
        avg_change = sum(changes) / len(changes)
        
        # تحديد العتبة بناءً على حجم البيانات
        threshold = max(1.0, sum(data) / len(data) * 0.1)  # 10% من المتوسط
        
        if avg_change > threshold:
            return 'increasing'
        elif avg_change < -threshold:
            return 'decreasing'
        else:
            return 'stable'
            
    def get_user_trust_distribution(self):
        """توزيع درجات ثقة المستخدمين"""
        from django.db.models import Count, Case, When, IntegerField
        
        # استخدام SQL آمن
        distribution = User.objects.aggregate(
            very_high=Count(Case(When(trust_score__gte=90, then=1), output_field=IntegerField())),
            high=Count(Case(When(trust_score__gte=70, trust_score__lt=90, then=1), output_field=IntegerField())),
            medium=Count(Case(When(trust_score__gte=40, trust_score__lt=70, then=1), output_field=IntegerField())),
            low=Count(Case(When(trust_score__lt=40, then=1), output_field=IntegerField())),
        )
        
        return {k: v for k, v in distribution.items()}

    def get_report_demographics(self):
        """تحليلات ديموغرافية للبلاغات"""
        from reports.models import Report
        
        gender_dist = Report.objects.values('person__gender').annotate(count=Count('report_id')).order_by('person__gender')
        health_dist = Report.objects.values('health_at_loss').annotate(count=Count('report_id')).order_by('health_at_loss')

        return {
            'gender': {item['person__gender'] or 'unknown': item['count'] for item in gender_dist},
            'health_condition': {item['health_at_loss'] or 'غير محدد': item['count'] for item in health_dist if item['count'] > 0}
        }

    def cleanup_old_data(self, days_to_keep=90):
        """
        تنظيف البيانات القديمة
        """
        try:
            cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)
            
            # حذف الإحصائيات القديمة
            old_stats = DailyStats.objects.filter(date__lt=cutoff_date)
            stats_count = old_stats.count()
            old_stats.delete()
            
            # حذف التقارير القديمة
            from .models import AnalyticsReport
            old_reports = AnalyticsReport.objects.filter(
                generated_at__lt=timezone.now() - timedelta(days=days_to_keep),
                is_scheduled=False
            )
            reports_count = old_reports.count()
            old_reports.delete()
            
            logger.info(f"تم تنظيف {stats_count} إحصائية و {reports_count} تقرير قديم")
            
            return {
                'deleted_stats': stats_count,
                'deleted_reports': reports_count,
            }
            
        except Exception as e:
            logger.error(f"خطأ في تنظيف البيانات القديمة: {e}")
            return None