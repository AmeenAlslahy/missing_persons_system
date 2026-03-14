from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Governorate, District, Uzlah


class ActiveFilter(admin.SimpleListFilter):
    """فلتر مخصص للنشط"""
    title = _('الحالة')
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('active', _('نشط')),
            ('inactive', _('غير نشط')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_active=True)
        if self.value() == 'inactive':
            return queryset.filter(is_active=False)
        return queryset


@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ['name_colored', 'code', 'districts_count', 'uzlahs_count', 
                   'population', 'status_badge', 'order']
    list_filter = [ActiveFilter]
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    list_editable = ['order']
    readonly_fields = ['districts_count', 'uzlahs_count', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'name_ar', 'name_en', 'code')
        }),
        (_('معلومات إضافية'), {
            'fields': ('population', 'area', 'is_active', 'order')
        }),
        (_('إحصائيات'), {
            'fields': ('districts_count', 'uzlahs_count'),
            'classes': ('collapse',)
        }),
        (_('تواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_colored(self, obj):
        return format_html(
            '<span style="color: #2c3e50; font-weight: bold;">{}</span>',
            obj.name_ar or obj.name
        )
    name_colored.short_description = _('الاسم')
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #27ae60; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
                _('نشط')
            )
        return format_html(
            '<span style="background-color: #e74c3c; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
            _('غير نشط')
        )
    status_badge.short_description = _('الحالة')
    
    def uzlahs_count(self, obj):
        return obj.uzlahs_count
    uzlahs_count.short_description = _('عدد العزل')
    
    actions = ['activate_selected', 'deactivate_selected']
    
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _('تم تنشيط {} محافظة').format(updated))
    activate_selected.short_description = _('تنشيط المحددة')
    
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _('تم إلغاء تنشيط {} محافظة').format(updated))
    deactivate_selected.short_description = _('إلغاء تنشيط المحددة')


class UzlahInline(admin.TabularInline):
    model = Uzlah
    extra = 1
    fields = ['name', 'code', 'population', 'is_active', 'order']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name_colored', 'governorate', 'code', 'uzlahs_count', 'population', 'status_badge', 'order']
    list_filter = ['governorate', ActiveFilter]
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    list_editable = ['order']
    autocomplete_fields = ['governorate']
    inlines = [UzlahInline]
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('governorate', 'name', 'name_ar', 'name_en', 'code')
        }),
        (_('معلومات إضافية'), {
            'fields': ('population', 'is_active', 'order')
        }),
    )

    def name_colored(self, obj):
        return format_html(
            '<span style="color: #2c3e50; font-weight: bold;">{}</span>',
            obj.name_ar or obj.name
        )
    name_colored.short_description = _('الاسم')

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #27ae60; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
                _('نشط')
            )
        return format_html(
            '<span style="background-color: #e74c3c; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
            _('غير نشط')
        )
    status_badge.short_description = _('الحالة')


@admin.register(Uzlah)
class UzlahAdmin(admin.ModelAdmin):
    list_display = ['name_colored', 'district', 'governorate_name', 'code', 'population', 'status_badge', 'order']
    list_filter = ['district__governorate', 'district', ActiveFilter]
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    list_editable = ['order']
    autocomplete_fields = ['district']
    
    def governorate_name(self, obj):
        return obj.district.governorate.name_ar or obj.district.governorate.name
    governorate_name.short_description = _('المحافظة')
    governorate_name.admin_order_field = 'district__governorate__name'
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('district', 'name', 'name_ar', 'name_en', 'code')
        }),
        (_('معلومات إضافية'), {
            'fields': ('population', 'is_active', 'order')
        }),
    )

    def name_colored(self, obj):
        return format_html(
            '<span style="color: #2c3e50; font-weight: bold;">{}</span>',
            obj.name_ar or obj.name
        )
    name_colored.short_description = _('الاسم')

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #27ae60; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
                _('نشط')
            )
        return format_html(
            '<span style="background-color: #e74c3c; color: white; padding: 3px 10px; border-radius: 10px;">{}</span>',
            _('غير نشط')
        )
    status_badge.short_description = _('الحالة')