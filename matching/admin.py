from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import MatchResult, MatchingAuditLog, MatchFeedback


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = [
        'match_id_short', 'report_1_info', 'report_2_info', 
        'similarity_colored', 'confidence_level', 'priority_colored',
        'match_status_colored', 'detected_at'
    ]
    list_filter = ['match_status', 'confidence_level', 'match_type', 'priority_level', 'detected_at']
    search_fields = ['report_1__report_code', 'report_2__report_code', 
                     'report_1__person__first_name', 'report_2__person__first_name']
    readonly_fields = ['match_id', 'detected_at', 'updated_at', 'view_count']
    date_hierarchy = 'detected_at'
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('match_id', 'report_1', 'report_2')
        }),
        ('نتائج المطابقة', {
            'fields': ('similarity_score', 'confidence_level', 'match_type', 
                      'match_status', 'priority_level')
        }),
        ('التفاصيل', {
            'fields': ('match_reason', 'match_details', 'view_count')
        }),
        ('المراجعة', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('detected_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'report_1', 'report_2', 'report_1__person', 'report_2__person'
        )
    
    def match_id_short(self, obj):
        return str(obj.match_id)[:8] + '...'
    match_id_short.short_description = 'المعرف'
    
    def report_1_info(self, obj):
        if obj.report_1 and obj.report_1.person:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.report_1.person.full_name,
                obj.report_1.report_code
            )
        return '-'
    report_1_info.short_description = 'البلاغ الأول'
    
    def report_2_info(self, obj):
        if obj.report_2 and obj.report_2.person:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.report_2.person.full_name,
                obj.report_2.report_code
            )
        return '-'
    report_2_info.short_description = 'البلاغ الثاني'
    
    def similarity_colored(self, obj):
        score = obj.similarity_score * 100
        color = 'green' if score >= 80 else 'orange' if score >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            round(score, 1)
        )
    similarity_colored.short_description = 'نسبة التشابه'
    
    def priority_colored(self, obj):
        colors = {
            'urgent': 'red',
            'high': 'orange',
            'normal': 'blue',
            'low': 'gray',
        }
        color = colors.get(obj.priority_level, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_level_display()
        )
    priority_colored.short_description = 'الأولوية'
    
    def match_status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'rejected': 'red',
            'false_positive': 'gray',
            'reviewing': 'blue',
        }
        color = colors.get(obj.match_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_match_status_display()
        )
    match_status_colored.short_description = 'الحالة'
    
    actions = ['accept_matches', 'reject_matches', 'mark_as_false_positive']
    
    def accept_matches(self, request, queryset):
        updated = queryset.update(
            match_status='accepted',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'تم قبول {updated} مطابقة')
    accept_matches.short_description = 'قبول المطابقات المحددة'
    
    def reject_matches(self, request, queryset):
        updated = queryset.update(
            match_status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'تم رفض {updated} مطابقة')
    reject_matches.short_description = 'رفض المطابقات المحددة'
    
    def mark_as_false_positive(self, request, queryset):
        updated = queryset.update(
            match_status='false_positive',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'تم تصنيف {updated} مطابقة كإيجابية خاطئة')
    mark_as_false_positive.short_description = 'تصنيف كإيجابية خاطئة'


@admin.register(MatchingAuditLog)
class MatchingAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'status', 'report_count', 'processing_time', 'timestamp']
    list_filter = ['action_type', 'status', 'timestamp']
    search_fields = ['message']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MatchFeedback)
class MatchFeedbackAdmin(admin.ModelAdmin):
    list_display = ['match', 'user', 'is_correct', 'rating', 'created_at']
    list_filter = ['is_correct', 'rating', 'created_at']
    search_fields = ['user__phone', 'user__first_name', 'comments']
    readonly_fields = ['created_at']