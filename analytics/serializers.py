from rest_framework import serializers
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import DailyStats, PerformanceMetric, AnalyticsReport, DashboardWidget
from accounts.models import User

# استخدام StringRelatedField بدلاً من UserProfileSerializer لتجنب Circular Import
class UserSimpleSerializer(serializers.ModelSerializer):
    """سرياليزر مبسط للمستخدم"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name', 'user_type']


class DailyStatsSerializer(serializers.ModelSerializer):
    """سرياليزر للإحصائيات اليومية"""
    date_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyStats
        fields = [
            'date', 'date_display', 'total_users', 'new_users', 'active_users',
            'verified_users', 'total_reports', 'new_reports', 'missing_reports',
            'found_reports', 'resolved_reports', 'pending_review_reports',
            'resolved_today', 'resolved_this_week', 'resolved_this_month',
            'total_matches', 'new_matches', 'accepted_matches',
            'false_positive_matches', 'match_success_rate', 'total_logins',
            'total_searches', 'total_notifications', 'avg_response_time',
            'avg_resolution_time', 'system_uptime', 'error_rate', 
            'top_cities', 'reports_by_gender', 'reports_by_age_group', 
            'calculated_at'
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
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    
    class Meta:
        model = PerformanceMetric
        fields = [
            'metric_id', 'metric_name', 'metric_description', 'current_value',
            'target_value', 'min_value', 'max_value', 'unit', 'category',
            'category_display', 'direction', 'direction_display', 'status', 
            'status_display', 'percentage', 'threshold_warning', 
            'threshold_critical', 'last_updated', 'update_frequency', 'is_active'
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
        return round(obj.get_percentage(), 1)


class AnalyticsReportSerializer(serializers.ModelSerializer):
    """سرياليزر للتقارير التحليلية"""
    period_display = serializers.SerializerMethodField()
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    schedule_frequency_display = serializers.CharField(
        source='get_schedule_frequency_display', read_only=True
    )
    allowed_users_data = UserSimpleSerializer(source='allowed_users', many=True, read_only=True)
    
    class Meta:
        model = AnalyticsReport
        fields = [
            'report_id', 'report_name', 'report_type', 'report_type_display',
            'description', 'filters', 'data', 'charts', 'insights', 
            'recommendations', 'period_start', 'period_end', 'period_display',
            'generated_at', 'is_scheduled', 'schedule_frequency',
            'schedule_frequency_display', 'export_formats', 'last_run', 
            'next_run', 'status', 'status_display', 'is_public', 
            'allowed_users', 'allowed_users_data'
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
    widget_type_display = serializers.CharField(source='get_widget_type_display', read_only=True)
    data_source_display = serializers.CharField(source='get_data_source_display', read_only=True)
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    
    class Meta:
        model = DashboardWidget
        fields = [
            'widget_id', 'widget_name', 'widget_type', 'widget_type_display',
            'data_source', 'data_source_display', 'query', 'filters', 'title',
            'description', 'size', 'size_display', 'column', 'row', 'order',
            'refresh_interval', 'allowed_roles', 'is_active', 'is_public',
            'widget_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['widget_id', 'created_at', 'updated_at', 'widget_data']
        # منع drf-yasg من استدعاء get_widget_data أثناء schema generation
        swagger_schema_fields = {
            'example': {
                'widget_id': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                'widget_name': 'Report Stats',
                'widget_data': {}
            }
        }
    
    def get_widget_data(self, obj):
        """الحصول على بيانات العنصر"""
        try:
            request = self.context.get('request')
            return obj.get_data(user=request.user if request else None)
        except Exception as e:
            return {'error': str(e)}


class GenerateReportSerializer(serializers.Serializer):
    """سرياليزر لتوليد تقرير"""
    REPORT_TYPES = [
        ('performance', 'أداء'),
        ('user', 'مستخدمين'),
        ('reports', 'بلاغات'),
        ('matching', 'مطابقة'),
        ('custom', 'مخصص'),
    ]
    
    report_type = serializers.ChoiceField(choices=REPORT_TYPES, required=True)
    report_name = serializers.CharField(max_length=200, required=True)
    period_start = serializers.DateField(required=True)
    period_end = serializers.DateField(required=True)
    filters = serializers.JSONField(required=False, allow_null=True, default=dict)
    is_public = serializers.BooleanField(default=False)
    generate_now = serializers.BooleanField(default=True)
    
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