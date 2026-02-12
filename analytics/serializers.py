from rest_framework import serializers
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import DailyStats, PerformanceMetric, AnalyticsReport, DashboardWidget
from accounts.serializers import UserProfileSerializer


class DailyStatsSerializer(serializers.ModelSerializer):
    """سرياليزر للإحصائيات اليومية"""
    date_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyStats
        fields = [
            'date', 'date_display', 'total_users', 'new_users', 'active_users',
            'verified_users', 'total_reports', 'new_reports', 'missing_reports',
            'found_reports', 'resolved_reports', 'pending_review_reports',
            'total_matches', 'new_matches', 'accepted_matches',
            'false_positive_matches', 'match_success_rate', 'total_logins',
            'total_searches', 'total_notifications', 'avg_response_time',
            'system_uptime', 'error_rate', 'top_cities', 'reports_by_gender',
            'reports_by_age_group', 'calculated_at'
        ]
        read_only_fields = ['calculated_at']
    
    def get_date_display(self, obj):
        """تنسيق التاريخ للعرض"""
        return obj.date.strftime('%Y-%m-%d')


class PerformanceMetricSerializer(serializers.ModelSerializer):
    """سرياليزر لمقاييس الأداء"""
    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PerformanceMetric
        fields = [
            'metric_id', 'metric_name', 'metric_description', 'current_value',
            'target_value', 'min_value', 'max_value', 'unit', 'category',
            'direction', 'status', 'status_display', 'percentage',
            'threshold_warning', 'threshold_critical', 'last_updated',
            'update_frequency', 'is_active'
        ]
        read_only_fields = ['metric_id', 'last_updated']
    
    def get_status(self, obj):
        """الحصول على حالة المقياس"""
        status, _ = obj.get_status()
        return status
    
    def get_status_display(self, obj):
        """الحصول على عرض حالة المقياس"""
        _, display = obj.get_status()
        return display
    
    def get_percentage(self, obj):
        """الحصول على النسبة المئوية"""
        return obj.get_percentage()


class AnalyticsReportSerializer(serializers.ModelSerializer):
    """سرياليزر للتقارير التحليلية"""
    period_display = serializers.SerializerMethodField()
    allowed_users_data = UserProfileSerializer(source='allowed_users', many=True, read_only=True)
    
    class Meta:
        model = AnalyticsReport
        fields = [
            'report_id', 'report_name', 'report_type', 'description',
            'filters', 'data', 'charts', 'insights', 'recommendations',
            'period_start', 'period_end', 'period_display', 'generated_at',
            'is_scheduled', 'schedule_frequency', 'export_formats',
            'last_run', 'next_run', 'status', 'is_public', 'allowed_users',
            'allowed_users_data'
        ]
        read_only_fields = ['report_id', 'generated_at', 'last_run']
    
    def get_period_display(self, obj):
        """تنسيق الفترة للعرض"""
        return f"{obj.period_start} إلى {obj.period_end}"
    
    def validate(self, data):
        """التحقق من صحة البيانات"""
        if data.get('period_start') and data.get('period_end'):
            if data['period_start'] > data['period_end']:
                raise serializers.ValidationError({
                    'period_start': 'تاريخ البداية يجب أن يكون قبل تاريخ النهاية',
                    'period_end': 'تاريخ النهاية يجب أن يكون بعد تاريخ البداية'
                })
        
        return data


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """سرياليزر لعناصر لوحة التحكم"""
    widget_data = serializers.SerializerMethodField()
    
    class Meta:
        model = DashboardWidget
        fields = [
            'widget_id', 'widget_name', 'widget_type', 'data_source',
            'query', 'filters', 'title', 'description', 'size', 'column',
            'row', 'order', 'refresh_interval', 'allowed_roles',
            'is_active', 'is_public', 'widget_data', 'created_at',
            'updated_at'
        ]
        read_only_fields = ['widget_id', 'created_at', 'updated_at', 'widget_data']
    
    def get_widget_data(self, obj):
        """الحصول على بيانات العنصر"""
        try:
            return obj.get_data()
        except Exception:
            return {}


class GenerateReportSerializer(serializers.Serializer):
    """سرياليزر لتوليد تقرير"""
    report_type = serializers.ChoiceField(
        choices=AnalyticsReport.report_type.field.choices,
        required=True
    )
    report_name = serializers.CharField(max_length=200, required=True)
    period_start = serializers.DateField(required=True)
    period_end = serializers.DateField(required=True)
    filters = serializers.JSONField(required=False, allow_null=True)
    is_public = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """التحقق من صحة البيانات"""
        if data['period_start'] > data['period_end']:
            raise serializers.ValidationError({
                'period_start': 'تاريخ البداية يجب أن يكون قبل تاريخ النهاية'
            })
        
        # التحقق من أن الفترة لا تزيد عن سنة
        delta = data['period_end'] - data['period_start']
        if delta.days > 365:
            raise serializers.ValidationError({
                'period_end': 'لا يمكن إنشاء تقرير لفترة تزيد عن سنة'
            })
        
        return data


class DateRangeSerializer(serializers.Serializer):
    """سرياليزر لنطاق التاريخ"""
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    
    def validate(self, data):
        """التحقق من صحة البيانات"""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError({
                'start_date': 'تاريخ البداية يجب أن يكون قبل تاريخ النهاية'
            })
        
        # التحقق من أن الفترة لا تزيد عن 90 يوم
        delta = data['end_date'] - data['start_date']
        if delta.days > 90:
            raise serializers.ValidationError({
                'end_date': 'لا يمكن طلب بيانات لفترة تزيد عن 90 يوم'
            })
        
        return data


class DashboardDataSerializer(serializers.Serializer):
    """سرياليزر لبيانات لوحة التحكم"""
    widgets = DashboardWidgetSerializer(many=True, read_only=True)
    daily_stats = serializers.DictField(read_only=True)
    performance_metrics = PerformanceMetricSerializer(many=True, read_only=True)
    recent_reports = AnalyticsReportSerializer(many=True, read_only=True)
    user_role = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
