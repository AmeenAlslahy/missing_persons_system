from django.contrib import admin
from django.utils.html import format_html
from .models import Report, ReportImage, Category, GeographicalArea, ReportAuditLog


class ReportImageInline(admin.TabularInline):
    model = ReportImage
    extra = 0
    fields = ['image', 'face_detected', 'quality_score', 'processing_status']
    readonly_fields = ['face_detected', 'quality_score', 'processing_status']


class ReportAuditLogInline(admin.TabularInline):
    model = ReportAuditLog
    extra = 0
    readonly_fields = ['user', 'action_type', 'action_details', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['report_code', 'person_name', 'report_type', 'status', 'city', 'created_at', 'requires_admin_review']
    list_filter = ['report_type', 'status', 'requires_admin_review', 'city', 'created_at']
    search_fields = ['report_code', 'person_name', 'contact_phone', 'last_seen_location']
    readonly_fields = ['report_code', 'created_at', 'updated_at', 'resolved_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('report_code', 'user', 'report_type', 'status', 'requires_admin_review')
        }),
        ('معلومات الشخص', {
            'fields': ('person_name', 'age', 'gender', 'nationality', 'primary_photo')
        }),
        ('الوصف البدني', {
            'fields': ('height', 'weight', 'body_build', 'skin_color', 'eye_color', 
                      'hair_color', 'hair_type', 'distinctive_features', 'scars_marks', 'tattoos')
        }),
        ('معلومات الفقدان/العثور', {
            'fields': ('last_seen_location', 'last_seen_date', 'last_seen_time',
                      'missing_from', 'circumstances', 'found_location', 'found_date',
                      'current_location', 'health_condition')
        }),
        ('معلومات الاتصال', {
            'fields': ('contact_person', 'contact_phone', 'contact_email', 'contact_relationship')
        }),
        ('المعلومات الجغرافية', {
            'fields': ('city', 'district', 'latitude', 'longitude')
        }),
        ('المراجعة الإدارية', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at', 'resolved_at')
        }),
    )
    
    inlines = [ReportImageInline, ReportAuditLogInline]
    
    actions = ['mark_as_resolved', 'mark_as_active', 'require_review']
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f"تم تحديث {queryset.count()} بلاغ كتم الحل")
    mark_as_resolved.short_description = "تعيين كمحلول"
    
    def mark_as_active(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f"تم تحديث {queryset.count()} بلاغ كنشط")
    mark_as_active.short_description = "تعيين كنشط"
    
    def require_review(self, request, queryset):
        queryset.update(requires_admin_review=True)
        self.message_user(request, f"تم تعيين {queryset.count()} بلاغ لمراجعة المشرف")
    require_review.short_description = "طلب مراجعة مشرف"


@admin.register(ReportImage)
class ReportImageAdmin(admin.ModelAdmin):
    list_display = ['report', 'face_detected', 'quality_score', 'processing_status', 'uploaded_at']
    list_filter = ['face_detected', 'processing_status', 'uploaded_at']
    search_fields = ['report__report_code', 'report__person_name']
    readonly_fields = ['face_embedding', 'embedding_version', 'face_detected', 
                      'quality_score', 'uploaded_at', 'processed_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('report')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'priority_level', 'response_time_hours']
    list_filter = ['priority_level']
    search_fields = ['name', 'description']


@admin.register(GeographicalArea)
class GeographicalAreaAdmin(admin.ModelAdmin):
    list_display = ['area_name', 'city', 'active_volunteers', 'active_reports', 'updated_at']
    list_filter = ['city']
    search_fields = ['area_name', 'city', 'coordinator_name']


@admin.register(ReportAuditLog)
class ReportAuditLogAdmin(admin.ModelAdmin):
    list_display = ['report', 'user', 'action_type', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['report__report_code', 'user__email', 'action_details']
    readonly_fields = ['report', 'user', 'action_type', 'action_details', 
                      'old_data', 'new_data', 'changed_fields', 'ip_address', 
                      'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False