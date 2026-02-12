from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, VolunteerProfile, AuditLog
from django.utils.translation import gettext_lazy as _


class VolunteerProfileInline(admin.StackedInline):
    model = VolunteerProfile
    can_delete = False
    verbose_name_plural = 'معلومات المتطوع'
    fields = ['city', 'area', 'is_active_volunteer', 'skills', 'languages']


class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name', 'user_role', 'verification_status', 'is_active', 'date_joined']
    list_filter = ['user_role', 'verification_status', 'is_active', 'gender']
    search_fields = ['email', 'full_name', 'national_id', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('المعلومات الشخصية'), {
            'fields': ('full_name', 'national_id', 'date_of_birth', 'gender', 'phone', 'profile_picture')
        }),
        (_('معلومات الحساب'), {
            'fields': ('user_role', 'verification_status', 'trust_score', 'total_reports', 'resolved_reports')
        }),
        (_('الصلاحيات'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('تواريخ مهمة'), {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'user_role'),
        }),
    )
    
    inlines = [VolunteerProfileInline]
    
    def get_inline_instances(self, request, obj=None):
        """إظهار معلومات المتطوع فقط للمتطوعين"""
        if obj and obj.user_role in ['volunteer', 'admin', 'super_admin']:
            return [VolunteerProfileInline(self.model, self.admin_site)]
        return []


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'ip_address', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['user__email', 'user__full_name', 'action_details', 'ip_address']
    readonly_fields = ['user', 'action_type', 'action_details', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(User, UserAdmin)
admin.site.register(VolunteerProfile)
admin.site.register(AuditLog, AuditLogAdmin)