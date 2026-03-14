from django.utils import timezone
from datetime import timedelta
import logging
from django.core.cache import cache
from django.db.models import Count, Q, Avg, Case, When, IntegerField

from .models import DailyStats, PerformanceMetric
from reports.models import Report
from matching.models import MatchResult
from accounts.models import User

logger = logging.getLogger(__name__)


class AnalyticsService:
    """خدمة التحليلات والإحصائيات - محسنة مع كاش"""
    
    # ثوابت للكاش
    CACHE_TIMEOUT_SHORT = 300  # 5 دقائق
    CACHE_TIMEOUT_MEDIUM = 1800  # 30 دقيقة
    CACHE_TIMEOUT_LONG = 3600  # ساعة
    
    def __init__(self):
        self.cache_prefix = 'analytics_'
    
    def _get_cache_key(self, key):
        """إنشاء مفتاح كاش"""
        return f"{self.cache_prefix}{key}"
    
    def get_cached_data(self, key, compute_func, timeout=CACHE_TIMEOUT_MEDIUM):
        """
        الحصول على بيانات من الكاش أو حسابها
        """
        cache_key = self._get_cache_key(key)
        cached = cache.get(cache_key)
        
        if cached is not None:
            logger.debug(f"Cache hit for {key}")
            return cached
        
        logger.debug(f"Cache miss for {key}, computing...")
        data = compute_func()
        
        if data is not None:
            cache.set(cache_key, data, timeout)
        
        return data
    
    def invalidate_cache(self, key_pattern=None):
        """مسح الكاش"""
        if key_pattern:
            # مسح كاش محدد
            cache.delete(self._get_cache_key(key_pattern))
        else:
            # مسح كل كاش analytics
            # ملاحظة: هذا يتطلب تخزين كل المفاتيح أو استخدام cache.clear() بحذر
            pass
    
    def update_report_stats(self, report, created=False):
        """
        تحديث الإحصائيات عند تغيير تقرير
        """
        try:
            # تحديث إحصائيات اليوم
            self.update_daily_stats()
            
            # مسح كاش dashboard
            self.invalidate_cache('dashboard')
            
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
        matching_stats = self._update_matching_stats()
        
        # مسح الكاش
        self.invalidate_cache()
        
        return {
            'daily_stats': daily_stats,
            'matching_stats': matching_stats
        }

    def _update_matching_stats(self):
        """
        تحديث إحصائيات المطابقة
        """
        stats = {
            'total_matches': MatchResult.objects.count(),
            'accepted_matches': MatchResult.objects.filter(match_status='accepted').count(),
            'pending_matches': MatchResult.objects.filter(match_status='pending').count(),
            'rejected_matches': MatchResult.objects.filter(match_status='rejected').count(),
            'false_positive_matches': MatchResult.objects.filter(match_status='false_positive').count(),
            'avg_similarity': MatchResult.objects.aggregate(Avg('similarity_score'))['similarity_score__avg'] or 0,
        }
        
        # تخزين في كاش
        cache.set(
            self._get_cache_key('matching_stats'), 
            stats, 
            timeout=self.CACHE_TIMEOUT_MEDIUM
        )
        
        return stats

    def get_matching_stats(self):
        """الحصول على إحصائيات المطابقة مع كاش"""
        return self.get_cached_data(
            'matching_stats',
            self._update_matching_stats,
            timeout=self.CACHE_TIMEOUT_MEDIUM
        )

    def update_daily_stats(self, date=None):
        """
        تحديث الإحصائيات اليومية
        """
        try:
            if not date:
                date = timezone.now().date()
            
            stats = DailyStats.get_or_create_today()
            
            # مسح كاش dashboard المرتبط بهذا التاريخ
            self.invalidate_cache(f'dashboard_{date}')
            
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
                'active_users_rate': self._calculate_active_users_rate(),
                'verification_rate': self._calculate_verification_rate(),
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
            
            # مسح كاش performance metrics
            self.invalidate_cache('performance_metrics')
            
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
    
    def _calculate_active_users_rate(self):
        """حساب معدل المستخدمين النشطين"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active = User.objects.filter(last_login__gte=thirty_days_ago).count()
        total = User.objects.count()
        
        if total > 0:
            return (active / total) * 100
        return 0.0
    
    def _calculate_verification_rate(self):
        """حساب معدل توثيق المستخدمين"""
        verified = User.objects.filter(verification_status='verified').count()
        total = User.objects.count()
        
        if total > 0:
            return (verified / total) * 100
        return 0.0
    
    def _get_metric_description(self, metric_name):
        """الحصول على وصف المقياس"""
        descriptions = {
            'match_success_rate': 'نسبة المطابقات المقبولة من إجمالي المطابقات المراجعة',
            'resolution_rate': 'نسبة البلاغات التي تم حلها من إجمالي البلاغات',
            'active_users_rate': 'نسبة المستخدمين النشطين خلال آخر 30 يوم',
            'verification_rate': 'نسبة المستخدمين الموثوقين',
        }
        return descriptions.get(metric_name, 'مقياس أداء النظام')
    
    def _get_metric_category(self, metric_name):
        """الحصول على فئة المقياس"""
        categories = {
            'match_success_rate': 'matching',
            'resolution_rate': 'report',
            'active_users_rate': 'user',
            'verification_rate': 'user',
        }
        return categories.get(metric_name, 'system')
    
    def get_dashboard_stats(self, user=None):
        """
        إحصائيات لوحة التحكم موحدة - محسنة
        """
        def compute_dashboard_stats():
            today_stats = DailyStats.get_or_create_today()
            matching_stats = self.get_matching_stats()
            
            # إحصائيات البلاغات الحية
            reports_stats = {
                'total': Report.objects.count(),
                'active': Report.objects.filter(status='active').count(),
                'pending': Report.objects.filter(status='pending').count(),
                'resolved': Report.objects.filter(status='resolved').count(),
            }
            
            # إحصائيات المستخدمين
            users_stats = {
                'total': User.objects.count(),
                'active_30d': User.objects.filter(
                    last_login__gte=timezone.now() - timedelta(days=30)
                ).count(),
                'verified': User.objects.filter(verification_status='verified').count(),
            }
            
            # تحويل DailyStats إلى قاموس
            daily_dict = {
                'new_reports': today_stats.new_reports,
                'new_matches': today_stats.new_matches,
                'new_users': today_stats.new_users,
                'match_success_rate': today_stats.match_success_rate,
                'avg_resolution_time': today_stats.avg_resolution_time,
                'resolved_today': today_stats.resolved_today,
                'resolved_this_week': today_stats.resolved_this_week,
                'resolved_this_month': today_stats.resolved_this_month,
            }
            
            return {
                'daily': daily_dict,
                'matching': matching_stats,
                'reports': reports_stats,
                'users': users_stats,
            }
        
        # استخدام كاش مع مدة مناسبة
        cache_key = 'dashboard'
        if user and not user.is_staff:
            # للمستخدمين العاديين، نستخدم كاش أقصر
            timeout = self.CACHE_TIMEOUT_SHORT
        else:
            timeout = self.CACHE_TIMEOUT_MEDIUM
        
        return self.get_cached_data(cache_key, compute_dashboard_stats, timeout)
    
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
            
            if not daily_stats.exists():
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
            insights.append("📈 عدد البلاغات الجديدة في تزايد مستمر")
        elif reports_trend == 'decreasing':
            insights.append("📉 عدد البلاغات الجديدة في تناقص")
        
        if matches_trend == 'increasing':
            insights.append("🤖 عدد المطابقات المكتشفة في تزايد")
        
        if users_trend == 'increasing':
            insights.append("👥 عدد المستخدمين الجدد في تزايد")
        
        # تحليل معدل النجاح
        success_rates = [stat.match_success_rate for stat in daily_stats if stat.match_success_rate > 0]
        if success_rates:
            avg_success = sum(success_rates) / len(success_rates)
            if avg_success < 70:
                insights.append(f"⚠️ معدل نجاح المطابقة منخفض ({avg_success:.1f}%)")
            elif avg_success > 90:
                insights.append(f"✨ معدل نجاح المطابقة ممتاز ({avg_success:.1f}%)")
        
        return insights if insights else ["📊 الأداء مستقر خلال الفترة المحددة"]
    
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
        distribution = User.objects.aggregate(
            very_high=Count(Case(When(trust_score__gte=90, then=1), output_field=IntegerField())),
            high=Count(Case(When(trust_score__gte=70, trust_score__lt=90, then=1), output_field=IntegerField())),
            medium=Count(Case(When(trust_score__gte=40, trust_score__lt=70, then=1), output_field=IntegerField())),
            low=Count(Case(When(trust_score__lt=40, then=1), output_field=IntegerField())),
        )
        
        return {k: v for k, v in distribution.items()}

    def get_report_demographics(self):
        """تحليلات ديموغرافية للبلاغات"""
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
            
            # مسح الكاش
            self.invalidate_cache()
            
            logger.info(f"تم تنظيف {stats_count} إحصائية و {reports_count} تقرير قديم")
            
            return {
                'deleted_stats': stats_count,
                'deleted_reports': reports_count,
            }
            
        except Exception as e:
            logger.error(f"خطأ في تنظيف البيانات القديمة: {e}")
            return None