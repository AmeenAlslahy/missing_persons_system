from django.contrib import admin
from django.utils.html import format_html
from .models import (
    FaceEmbedding, MatchResult, MatchReview, 
    MatchingConfig, MatchingAuditLog
)


@admin.register(FaceEmbedding)
class FaceEmbeddingAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_person_name', 'embedding_version', 
                   'quality_score', 'processing_status', 'created_at']
    list_filter = ['processing_status', 'embedding_version', 'created_at']
    search_fields = ['image__report__person_name', 'image__report__report_code']
    readonly_fields = ['embedding_vector', 'face_analysis', 'created_at', 'processed_at']
    
    def get_person_name(self, obj):
        return obj.image.report.person_name
    get_person_name.short_description = 'اسم الشخص'
    get_person_name.admin_order_field = 'image__report__person_name'


class MatchReviewInline(admin.TabularInline):
    model = MatchReview
    extra = 0
    readonly_fields = ['reviewer', 'decision', 'notes', 'reviewed_at']
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ['match_id', 'missing_person', 'found_person', 
                   'similarity_score', 'confidence_level', 'match_status', 'detected_at']
    list_filter = ['match_status', 'confidence_level', 'match_type', 'detected_at']
    search_fields = [
        'missing_report__person_name', 'missing_report__report_code',
        'found_report__person_name', 'found_report__report_code'
    ]
    readonly_fields = ['match_id', 'similarity_score', 'confidence_score', 
                      'detected_at', 'updated_at', 'resolved_at']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('match_id', 'missing_report', 'found_report')
        }),
        ('النتائج', {
            'fields': ('similarity_score', 'confidence_score', 'confidence_level')
        }),
        ('الحالة والنوع', {
            'fields': ('match_type', 'match_status')
        }),
        ('المراجعة', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('التواصل', {
            'fields': ('communication_opened', 'communication_details')
        }),
        ('التفاصيل', {
            'fields': ('match_details', 'matched_features')
        }),
        ('التواريخ', {
            'fields': ('detected_at', 'updated_at', 'resolved_at')
        }),
    )
    
    inlines = [MatchReviewInline]
    
    actions = ['accept_matches', 'reject_matches', 'mark_as_false_positive']
    
    def missing_person(self, obj):
        return obj.missing_report.person_name
    missing_person.short_description = 'الشخص المفقود'
    
    def found_person(self, obj):
        return obj.found_report.person_name
    found_person.short_description = 'الشخص المعثور عليه'
    
    def accept_matches(self, request, queryset):
        for match in queryset:
            match.accept_match(request.user, 'تم القبول عبر لوحة التحكم')
        self.message_user(request, f"تم قبول {queryset.count()} مطابقة")
    accept_matches.short_description = "قبول المطابقات المحددة"
    
    def reject_matches(self, request, queryset):
        for match in queryset:
            match.reject_match(request.user, 'تم الرفض عبر لوحة التحكم')
        self.message_user(request, f"تم رفض {queryset.count()} مطابقة")
    reject_matches.short_description = "رفض المطابقات المحددة"
    
    def mark_as_false_positive(self, request, queryset):
        for match in queryset:
            match.reject_match(request.user, 'إيجابي خاطئ', true)
        self.message_user(request, f"تم تعيين {queryset.count()} كمطابقة إيجابية خاطئة")
    mark_as_false_positive.short_description = "تعيين كإيجابي خاطئ"


@admin.register(MatchReview)
class MatchReviewAdmin(admin.ModelAdmin):
    list_display = ['match', 'reviewer', 'decision', 'reviewed_at']
    list_filter = ['decision', 'reviewed_at']
    search_fields = ['match__missing_report__person_name', 'match__found_report__person_name']
    readonly_fields = ['reviewer', 'decision', 'notes', 'evidence_links', 'reviewed_at']
    
    def has_add_permission(self, request):
        return False


@admin.register(MatchingConfig)
class MatchingConfigAdmin(admin.ModelAdmin):
    list_display = ['config_name', 'similarity_threshold', 'confidence_threshold', 
                   'auto_match_enabled', 'updated_at']
    list_filter = ['auto_match_enabled']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('config_name',)
        }),
        ('العتبات', {
            'fields': ('similarity_threshold', 'confidence_threshold')
        }),
        ('إعدادات المطابقة', {
            'fields': ('enable_face_matching', 'enable_data_matching', 
                      'enable_hybrid_matching', 'face_weight', 'data_weight')
        }),
        ('إعدادات الذكاء الاصطناعي', {
            'fields': ('ai_model_version', 'embedding_size')
        }),
        ('التشغيل التلقائي', {
            'fields': ('auto_match_enabled', 'match_interval_hours', 'last_run_at')
        }),
        ('الإشعارات', {
            'fields': ('notify_on_high_confidence', 'notify_on_match')
        }),
    )


@admin.register(MatchingAuditLog)
class MatchingAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'user', 'processing_time', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['action_details', 'user__email']
    readonly_fields = ['log_id', 'action_type', 'action_details', 'metadata', 
                      'user', 'created_at', 'processing_time']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False