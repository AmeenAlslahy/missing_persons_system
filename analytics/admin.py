from django.contrib import admin
from django.utils.html import format_html
from .models import DailyStats, PerformanceMetric, AnalyticsReport, DashboardWidget


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'new_reports', 'new_matches', 'new_users', 
                   'match_success_rate', 'calculated_at']
    list_filter = ['date']
    search_fields = ['date']
    readonly_fields = ['calculated_at']
    date_hierarchy = 'date'
    
    actions = ['recalculate_stats']
    
    def recalculate_stats(self, request, queryset):
        """إعادة حساب الإحصائيات المحددة"""
        for stats in queryset:
            stats.calculate_stats()
        self.message_user(request, f"تم إعادة حساب {queryset.count()} إحصائية")
    recalculate_stats.short_description = "إعادة حساب الإحصائيات"


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'current_value', 'target_value', 'unit', 
                   'category', 'status_colored', 'last_updated']
    list_filter = ['category', 'is_active']
    search_fields = ['metric_name', 'metric_description']
    readonly_fields = ['metric_id', 'last_updated']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('metric_name', 'metric_description', 'category', 'unit')
        }),
        ('القيم', {
            'fields': ('current_value', 'target_value', 'min_value', 'max_value')
        }),
        ('الإعدادات', {
            'fields': ('direction', 'update_frequency', 'is_active',
                      'threshold_warning', 'threshold_critical')
        }),
    )
    
    def status_colored(self, obj):
        status, display = obj.get_status()
        colors = {
            'healthy': 'green',
            'warning': 'orange',
            'critical': 'red',
            'unknown': 'gray'
        }
        color = colors.get(status, 'gray')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, display
        )
    status_colored.short_description = 'الحالة'


@admin.register(AnalyticsReport)
class AnalyticsReportAdmin(admin.ModelAdmin):
    list_display = ['report_name', 'report_type', 'period_start', 'period_end',
                   'status', 'is_public', 'generated_at']
    list_filter = ['report_type', 'status', 'is_public', 'generated_at']
    search_fields = ['report_name', 'description']
    readonly_fields = ['report_id', 'generated_at', 'last_run']
    filter_horizontal = ['allowed_users']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('report_name', 'report_type', 'description')
        }),
        ('الفترة', {
            'fields': ('period_start', 'period_end')
        }),
        ('البيانات', {
            'fields': ('filters', 'data', 'charts', 'insights', 'recommendations')
        }),
        ('الجدولة', {
            'fields': ('is_scheduled', 'schedule_frequency', 'next_run')
        }),
        ('التصدير', {
            'fields': ('export_formats',)
        }),
        ('الوصول', {
            'fields': ('is_public', 'allowed_users')
        }),
        ('الحالة', {
            'fields': ('status',)
        }),
    )
    
    actions = ['generate_reports', 'export_reports']
    
    def generate_reports(self, request, queryset):
        """توليد التقارير المحددة"""
        for report in queryset:
            report.generate_report()
        self.message_user(request, f"تم توليد {queryset.count()} تقرير")
    generate_reports.short_description = "توليد التقارير"
    
    def export_reports(self, request, queryset):
        """تصدير التقارير (محاكاة)"""
        self.message_user(request, f"سيتم تصدير {queryset.count()} تقرير")
    export_reports.short_description = "تصدير التقارير"


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['widget_name', 'widget_type', 'data_source', 'size',
                   'is_active', 'order', 'updated_at']
    list_filter = ['widget_type', 'data_source', 'is_active', 'is_public']
    search_fields = ['widget_name', 'title', 'description']
    readonly_fields = ['widget_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('widget_name', 'widget_type', 'title', 'description')
        }),
        ('البيانات', {
            'fields': ('data_source', 'query', 'filters')
        }),
        ('العرض', {
            'fields': ('size', 'column', 'row', 'order')
        }),
        ('الإعدادات', {
            'fields': ('refresh_interval', 'allowed_roles')
        }),
        ('الحالة', {
            'fields': ('is_active', 'is_public')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """تحديد الحقول المقروءة فقط"""
        if obj:  # عند التعديل
            return self.readonly_fields + ['widget_id']
        return self.readonly_fields