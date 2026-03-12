from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from django.utils.translation import gettext_lazy as _


class UserAdmin(BaseUserAdmin):
    list_display = ['phone', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active']
    search_fields = ['phone', 'first_name', 'last_name', 'email']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        (_('المعلومات الشخصية'), {
            'fields': ('first_name', 'middle_name', 'last_name', 'email')
        }),
        (_('العنوان'), {
            'fields': ('governorate', 'district', 'uzlah')
        }),
        (_('الصلاحيات'), {
            'fields': ('is_active', 'is_superuser', 'groups', 'user_permissions', 'user_type')
        }),
        (_('تواريخ مهمة'), {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


admin.site.register(User, UserAdmin)