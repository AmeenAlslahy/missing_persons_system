from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user_info', 'action_colored', 'resource_info', 'ip_address']
    list_filter = ['action', 'resource_type', 'timestamp']
    search_fields = ['user__phone', 'user__first_name', 'resource_id', 'ip_address']
    readonly_fields = ['timestamp', 'ip_address', 'user_agent', 'data_before', 'data_after']
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def user_info(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.user.full_name,
                obj.user.phone
            )
        return 'النظام'
    user_info.short_description = 'المستخدم'
    
    def action_colored(self, obj):
        colors = {
            'CREATE': 'green',
            'UPDATE': 'orange',
            'DELETE': 'red',
            'LOGIN': 'blue',
            'LOGOUT': 'gray',
        }
        color = colors.get(obj.action, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_colored.short_description = 'العملية'
    
    def resource_info(self, obj):
        if obj.resource_id:
            return format_html(
                '<strong>{}</strong><br><small>ID: {}</small>',
                obj.resource_type,
                obj.resource_id
            )
        return obj.resource_type
    resource_info.short_description = 'المورد'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser