from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Person, Report, ReportImage


class ReportImageInline(admin.TabularInline):
    model = ReportImage
    extra = 0
    fields = ['image_preview', 'quality_score', 'upload_at']
    readonly_fields = ['image_preview', 'quality_score', 'upload_at']
    
    def image_preview(self, obj):
        if obj.image_path:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 4px;" />',
                obj.image_path.url
            )
        return "-"
    image_preview.short_description = _('معاينة')


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'gender', 'age', 'created_at']
    list_filter = ['gender', 'created_at']
    search_fields = ['first_name', 'middle_name', 'last_name']
    readonly_fields = ['person_id', 'created_at', 'updated_at', 'age']
    
    fieldsets = (
        (_('الاسم'), {
            'fields': ('first_name', 'middle_name', 'last_name')
        }),
        (_('المعلومات الأساسية'), {
            'fields': ('date_of_birth', 'gender', 'blood_type')
        }),
        (_('الصفات'), {
            'fields': ('chronic_conditions', 'permanent_marks')
        }),
        (_('موقع السكن'), {
            'fields': ('home_governorate', 'home_district', 'home_uzlah')
        }),
        (_('تواريخ'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def age(self, obj):
        return obj.age
    age.short_description = _('العمر')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['report_code', 'person_name', 'report_type', 'status', 
                   'importance', 'lost_governorate', 'created_at']
    list_filter = ['report_type', 'status', 'importance', 'created_at']
    search_fields = ['report_code', 'person__first_name', 'person__last_name']
    readonly_fields = ['report_id', 'report_code', 'created_at', 'updated_at', 'resolved_at']
    autocomplete_fields = ['person', 'user', 'lost_governorate', 'lost_district']
    inlines = [ReportImageInline]
    
    fieldsets = (
        (_('معلومات البلاغ'), {
            'fields': ('report_id', 'report_code', 'user', 'person', 'report_type')
        }),
        (_('الموقع'), {
            'fields': ('lost_governorate', 'lost_district', 'lost_uzlah', 'lost_location_details')
        }),
        (_('آخر مشاهدة'), {
            'fields': ('last_seen_date', 'last_seen_time')
        }),
        (_('الوصف'), {
            'fields': ('health_at_loss', 'medications', 'clothing_description', 'possessions')
        }),
        (_('الاتصال'), {
            'fields': ('contact_phone', 'contact_person')
        }),
        (_('حالة البلاغ'), {
            'fields': ('status', 'importance', 'close_reason')
        }),
        (_('تواريخ'), {
            'fields': ('created_at', 'updated_at', 'resolved_at')
        }),
    )
    
    def person_name(self, obj):
        return obj.person.full_name
    person_name.short_description = _('اسم الشخص')
    person_name.admin_order_field = 'person__first_name'
    
    actions = ['approve_reports', 'reject_reports']
    
    def approve_reports(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, _('تمت الموافقة على %d بلاغ') % updated)
    approve_reports.short_description = _('موافقة على البلاغات المحددة')
    
    def reject_reports(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, _('تم رفض %d بلاغ') % updated)
    reject_reports.short_description = _('رفض البلاغات المحددة')


@admin.register(ReportImage)
class ReportImageAdmin(admin.ModelAdmin):
    list_display = ['report', 'image_preview', 'quality_score', 'upload_at']
    readonly_fields = ['face_embedding', 'quality_score', 'upload_at', 'image_preview']
    
    def image_preview(self, obj):
        if obj.image_path:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 4px;" />',
                obj.image_path.url
            )
        return "-"
    image_preview.short_description = _('معاينة')