from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
import logging

from .models import DailyStats, PerformanceMetric, AnalyticsReport, DashboardWidget
from .serializers import (
    DailyStatsSerializer, PerformanceMetricSerializer,
    AnalyticsReportSerializer, DashboardWidgetSerializer,
    GenerateReportSerializer, DateRangeSerializer,
    DashboardDataSerializer
)
from .services import AnalyticsService
from accounts.permissions import IsVolunteerOrHigher
from reports.models import Report
from matching.models import MatchResult
from accounts.models import User

logger = logging.getLogger(__name__)


class DailyStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet للإحصائيات اليومية"""
    serializer_class = DailyStatsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date']
    
    def get_queryset(self):
        """تصفية الإحصائيات بناءً على صلاحيات المستخدم"""
        queryset = DailyStats.objects.all().order_by('-date')
        
        # المستخدم العادي يرى فقط آخر 30 يوم
        if not self.request.user.is_staff:
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            queryset = queryset.filter(date__gte=thirty_days_ago)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def date_range(self, request):
        """الحصول على إحصائيات لفترة محددة"""
        serializer = DateRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        queryset = self.get_queryset().filter(
            date__gte=data['start_date'],
            date__lte=data['end_date']
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """ملخص الإحصائيات"""
        # الحصول على إحصائيات اليوم
        today_stats = DailyStats.get_or_create_today()
        
        # الحصول على إحصائيات الأمس للمقارنة
        yesterday = timezone.now().date() - timedelta(days=1)
        yesterday_stats = DailyStats.objects.filter(date=yesterday).first()
        
        # تحضير البيانات
        data = {
            'today': DailyStatsSerializer(today_stats).data if today_stats else {},
            'yesterday': DailyStatsSerializer(yesterday_stats).data if yesterday_stats else {},
            'comparison': self._calculate_comparison(today_stats, yesterday_stats)
        }
        
        return Response(data)
    
    def _calculate_comparison(self, today_stats, yesterday_stats):
        """حساب المقارنة بين اليوم والأمس"""
        if not today_stats or not yesterday_stats:
            return {}
        
        comparisons = {}
        
        # مقارنة البلاغات الجديدة
        if yesterday_stats.new_reports > 0:
            reports_change = ((today_stats.new_reports - yesterday_stats.new_reports) / yesterday_stats.new_reports) * 100
            comparisons['reports_change'] = round(reports_change, 1)
            comparisons['reports_trend'] = 'up' if reports_change > 0 else 'down'
        
        # مقارنة المطابقات الجديدة
        if yesterday_stats.new_matches > 0:
            matches_change = ((today_stats.new_matches - yesterday_stats.new_matches) / yesterday_stats.new_matches) * 100
            comparisons['matches_change'] = round(matches_change, 1)
            comparisons['matches_trend'] = 'up' if matches_change > 0 else 'down'
        
        # مقارنة المستخدمين الجدد
        if yesterday_stats.new_users > 0:
            users_change = ((today_stats.new_users - yesterday_stats.new_users) / yesterday_stats.new_users) * 100
            comparisons['users_change'] = round(users_change, 1)
            comparisons['users_trend'] = 'up' if users_change > 0 else 'down'
        
        return comparisons


class PerformanceMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet لمقاييس الأداء"""
    serializer_class = PerformanceMetricSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_active']
    
    def get_queryset(self):
        """تصفية المقاييس"""
        queryset = PerformanceMetric.objects.filter(is_active=True)
        
        # المستخدم العادي يرى فقط مقاييس النظام العامة
        if not self.request.user.is_staff:
            queryset = queryset.filter(category__in=['system', 'user'])
        
        return queryset.order_by('category', 'metric_name')
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """نظرة عامة على مقاييس الأداء"""
        metrics = self.get_queryset()
        
        # تجميع حسب الفئة
        categories = {}
        for metric in metrics:
            category = metric.category
            if category not in categories:
                categories[category] = []
            
            categories[category].append(PerformanceMetricSerializer(metric).data)
        
        # حساب المتوسط العام
        overall_health = self._calculate_overall_health(metrics)
        
        # حساب عدد المقاييس الصحية
        healthy_count = 0
        for metric in metrics:
            status, _ = metric.get_status()
            if status == 'healthy':
                healthy_count += 1
        
        return Response({
            'categories': categories,
            'overall_health': round(overall_health, 1),
            'total_metrics': metrics.count(),
            'healthy_metrics': healthy_count
        })
    
    def _calculate_overall_health(self, metrics):
        """حساب الصحة العامة للنظام"""
        if not metrics:
            return 100.0
        
        total_percentage = 0
        count = 0
        
        for metric in metrics:
            percentage = metric.get_percentage()
            total_percentage += percentage
            count += 1
        
        return total_percentage / count if count > 0 else 100.0


class AnalyticsReportViewSet(viewsets.ModelViewSet):
    """ViewSet للتقارير التحليلية"""
    serializer_class = AnalyticsReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'status', 'is_public']
    
    def get_queryset(self):
        """تصفية التقارير بناءً على صلاحيات المستخدم"""
        user = self.request.user
        
        if user.is_staff:
            # المشرف يرى كل التقارير
            queryset = AnalyticsReport.objects.all()
        else:
            # المستخدم العادي يرى التقارير العامة فقط
            queryset = AnalyticsReport.objects.filter(
                Q(is_public=True) | Q(allowed_users=user)
            ).distinct()
        
        return queryset.order_by('-generated_at')
    
    def get_permissions(self):
        """تحديد الصلاحيات"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """إنشاء تقرير جديد"""
        report = serializer.save()
        
        # إذا طلب توليد التقرير فوراً
        if self.request.data.get('generate_now', False):
            report.generate_report()
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """توليد التقرير"""
        report = self.get_object()
        
        # التحقق من الصلاحية
        if not request.user.is_staff and not report.is_public and request.user not in report.allowed_users.all():
            return Response(
                {'error': 'ليس لديك صلاحية توليد هذا التقرير'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        success = report.generate_report()
        
        if success:
            return Response({
                'message': 'تم توليد التقرير بنجاح',
                'report': AnalyticsReportSerializer(report).data
            })
        else:
            return Response({
                'error': 'فشل توليد التقرير'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """تصدير التقرير"""
        report = self.get_object()
        export_format = request.data.get('format', 'pdf')
        
        # التحقق من الصيغة المدعومة
        if export_format not in report.export_formats:
            return Response({
                'error': f'صيغة {export_format} غير مدعومة'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': f'سيتم تصدير التقرير بصيغة {export_format}',
            'download_url': f'/api/analytics/reports/{report.report_id}/download/{export_format}/',
            'estimated_time': '30 ثانية'
        })


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    """ViewSet لعناصر لوحة التحكم"""
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """تصفية العناصر بناءً على صلاحيات المستخدم"""
        user = self.request.user
        
        # الحصول على دور المستخدم
        user_role = user.user_type
        
        # العناصر العامة + العناصر الخاصة بدور المستخدم
        queryset = DashboardWidget.objects.filter(
            Q(is_public=True) | 
            Q(allowed_roles__contains=[user_role])
        ).filter(is_active=True).distinct()
        
        return queryset.order_by('column', 'row', 'order')
    
    def get_permissions(self):
        """تحديد الصلاحيات"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]


class DashboardView(APIView):
    """لوحة التحكم الرئيسية"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """الحصول على بيانات لوحة التحكم"""
        user = request.user
        
        try:
            # الحصول على عناصر لوحة التحكم المناسبة للمستخدم
            if user.is_staff:
                widgets = DashboardWidget.objects.filter(is_active=True).order_by('column', 'row', 'order')
            else:
                widgets = DashboardWidget.objects.filter(is_public=True, is_active=True).order_by('column', 'row', 'order')
            
            # الحصول على إحصائيات اليوم
            daily_stats = DailyStats.get_or_create_today()

            # الحصول على مقاييس الأداء
            if user.is_staff:
                metrics = PerformanceMetric.objects.filter(is_active=True)
            else:
                metrics = PerformanceMetric.objects.filter(is_active=True, category__in=['system', 'user'])

            # الحصول على التقارير الأخيرة
            if user.is_staff:
                recent_reports = AnalyticsReport.objects.all().order_by('-generated_at')[:5]
            else:
                recent_reports = AnalyticsReport.objects.filter(
                    Q(is_public=True) | Q(allowed_users=user)
                ).distinct().order_by('-generated_at')[:5]

            # إضافة بيانات إضافية للمخططات
            enhanced_daily_stats = DailyStatsSerializer(daily_stats).data if daily_stats else {}

            # إضافة بيانات حية
            total_reports_count = Report.objects.count()
            active_reports_count = Report.objects.filter(status='active').count()
            pending_reports_count = Report.objects.filter(status='pending').count()
            resolved_reports_count = Report.objects.filter(status='resolved').count()

            enhanced_daily_stats['total_reports'] = total_reports_count
            enhanced_daily_stats['active_reports'] = active_reports_count
            enhanced_daily_stats['pending_review_reports'] = pending_reports_count
            enhanced_daily_stats['resolved_reports'] = resolved_reports_count

            # إضافة بيانات المناطق الجغرافية
            top_cities = Report.objects.filter(lost_governorate__isnull=False).values('lost_governorate__name_ar').annotate(
                count=Count('report_id')
            ).order_by('-count')[:10]
            
            enhanced_daily_stats['top_cities'] = [
                {'city': item['lost_governorate__name_ar'], 'count': item['count']}
                for item in top_cities
            ]

            # حساب إحصائيات المطابقة والحل في الوقت الحقيقي
            total_matches = MatchResult.objects.count()
            enhanced_daily_stats['total_matches'] = total_matches
            
            total_accepted = MatchResult.objects.filter(match_status='accepted').count()
            total_reviewed = MatchResult.objects.filter(
                match_status__in=['accepted', 'rejected', 'false_positive']
            ).count()
            
            if total_reviewed > 0:
                match_success_rate = (total_accepted / total_reviewed) * 100
            else:
                total_reports = Report.objects.count()
                if total_reports > 0:
                    match_success_rate = (resolved_reports_count / total_reports) * 100
                else:
                    match_success_rate = 0.0
            enhanced_daily_stats['match_success_rate'] = match_success_rate

            # إحصائيات الحل الزمنية
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            
            resolved_today = Report.objects.filter(status='resolved', updated_at__gte=today_start).count()
            resolved_this_week = Report.objects.filter(status='resolved', updated_at__gte=week_start).count()
            
            enhanced_daily_stats['resolved_today'] = resolved_today
            enhanced_daily_stats['resolved_this_week'] = resolved_this_week

            # متوسط زمن الحل
            resolved_with_time = Report.objects.filter(
                status='resolved', created_at__isnull=False, updated_at__isnull=False
            )
            avg_time = 0.0
            if resolved_with_time.exists():
                total_hours = sum(
                    [(r.updated_at - r.created_at).total_seconds() / 3600 for r in resolved_with_time]
                )
                avg_time = total_hours / resolved_with_time.count()
            
            enhanced_daily_stats['avg_resolution_time'] = round(avg_time, 1)

            data = {
                'widgets': DashboardWidgetSerializer(widgets, many=True, context={'request': request}).data,
                'daily_stats': enhanced_daily_stats,
                'performance_metrics': PerformanceMetricSerializer(metrics, many=True).data,
                'recent_reports': AnalyticsReportSerializer(recent_reports, many=True, context={'request': request}).data,
                'user_role': user.user_type,
                'is_staff': user.is_staff
            }
            
            return Response(data)
            
        except Exception as e:
            logger.error(f"خطأ في DashboardView: {e}")
            return Response(
                {'error': 'حدث خطأ في تحميل بيانات لوحة التحكم'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateReportView(APIView):
    """إنشاء تقرير جديد"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """إنشاء وتوليد تقرير"""
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # إنشاء التقرير
        report = AnalyticsReport.objects.create(
            report_name=data['report_name'],
            report_type=data['report_type'],
            period_start=data['period_start'],
            period_end=data['period_end'],
            filters=data.get('filters', {}),
            is_public=data['is_public'],
            status='draft'
        )
        
        # إذا طلب المستخدم، توليد التقرير فوراً
        if request.data.get('generate_now', True):
            success = report.generate_report()
            
            if success:
                return Response({
                    'message': 'تم إنشاء وتوليد التقرير بنجاح',
                    'report': AnalyticsReportSerializer(report, context={'request': request}).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'تم إنشاء التقرير لكن فشل توليد البيانات',
                    'report': AnalyticsReportSerializer(report, context={'request': request}).data
                }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'message': 'تم إنشاء التقرير، سيتم توليده في الخلفية',
                'report': AnalyticsReportSerializer(report, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)


class AnalyticsStatisticsView(APIView):
    """إحصائيات التحليلات العامة"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # استخدام خدمة التحليلات
        service = AnalyticsService()

        # إحصائيات أساسية
        stats = {
            'system': {
                'total_reports': 0,
                'total_matches': 0,
                'total_users': 0,
                'match_success_rate': 0,
                'resolution_rate': 0,
            },
            'trends': {
                'reports_trend': 'stable',
                'matches_trend': 'stable',
                'users_trend': 'stable',
            }
        }

        try:
            # الحصول على إحصائيات هذا الشهر
            start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # حساب الإحصائيات الصحيحة
            total_reports = Report.objects.count()
            active_reports = Report.objects.filter(status='active').count()
            total_matches = MatchResult.objects.count()

            stats['system'].update({
                'total_reports': total_reports,
                'active_reports': active_reports,
                'this_month_reports': Report.objects.filter(created_at__gte=start_of_month).count(),
                'total_matches': total_matches,
                'this_month_matches': MatchResult.objects.filter(detected_at__gte=start_of_month).count(),
                'total_users': User.objects.count(),
                'this_month_users': User.objects.filter(date_joined__gte=start_of_month).count(),
                'match_success_rate': service._calculate_match_success_rate(),
                'resolution_rate': service._calculate_resolution_rate(),
            })

            # تحليل الاتجاهات
            last_30_days_stats = DailyStats.objects.filter(
                date__gte=timezone.now().date() - timedelta(days=30)
            ).order_by('date')

            if last_30_days_stats:
                stats['trends']['reports_trend'] = service.analyze_trend([s.new_reports for s in last_30_days_stats])
                stats['trends']['matches_trend'] = service.analyze_trend([s.new_matches for s in last_30_days_stats])
                stats['trends']['users_trend'] = service.analyze_trend([s.new_users for s in last_30_days_stats])
                
                trends_insights = service._generate_performance_insights(last_30_days_stats)
                stats['insights'] = trends_insights

            # بيانات إضافية للمخططات
            stats['user_trust'] = service.get_user_trust_distribution()
            stats['demographics'] = service.get_report_demographics()

        except Exception as e:
            logger.error(f"خطأ في AnalyticsStatisticsView: {e}")
            stats['error'] = 'حدث خطأ في تحميل الإحصائيات'

        return Response(stats)