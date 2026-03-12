from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Governorate, District, Uzlah


@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'districts_count', 'population', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    list_editable = ['order', 'is_active']
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'name_ar', 'name_en', 'code')
        }),
        (_('معلومات إضافية'), {
            'fields': ('population', 'area', 'is_active', 'order')
        }),
    )


class UzlahInline(admin.TabularInline):
    model = Uzlah
    extra = 1
    fields = ['name', 'code', 'population', 'is_active', 'order']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'governorate', 'code', 'uzlahs_count', 'population', 'is_active', 'order']
    list_filter = ['governorate', 'is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    list_editable = ['order', 'is_active']
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


@admin.register(Uzlah)
class UzlahAdmin(admin.ModelAdmin):
    list_display = ['name', 'district', 'governorate_name', 'code', 'population', 'is_active', 'order']
    list_filter = ['district__governorate', 'district', 'is_active']
    search_fields = ['name', 'name_ar', 'name_en', 'code']
    list_editable = ['order', 'is_active']
    autocomplete_fields = ['district']
    
    def governorate_name(self, obj):
        return obj.district.governorate.name
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