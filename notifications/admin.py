from django.contrib import admin
from .models import Notification, NotificationPreference
from django.utils.translation import gettext_lazy as _


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'user', 'title', 'notification_type',
                    'priority_level', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority_level', 'is_read', 'created_at']
    search_fields = ['user__phone', 'title', 'message']
    readonly_fields = ['notification_id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('notification_id', 'user', 'notification_type', 'title', 'message')
        }),
        ('الأولوية والحالة', {
            'fields': ('priority_level', 'is_read', 'read_at')
        }),
        ('الارتباطات', {
            'fields': ('related_report', 'related_match')
        }),
        ('الإجراءات', {
            'fields': ('action_required', 'action_url', 'action_text')
        }),
        ('البيانات الفنية', {
            'fields': ('metadata', 'expires_at', 'created_at')
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'push_enabled', 'sms_enabled', 'updated_at']
    list_filter = ['email_enabled', 'push_enabled', 'sms_enabled', 'updated_at']
    search_fields = ['user__phone', 'user__email']
    
    fieldsets = (
        ('المستخدم', {
            'fields': ('user',)
        }),
        ('القنوات المفعلة', {
            'fields': ('email_enabled', 'push_enabled', 'sms_enabled')
        }),
        ('تنبيهات الأحداث', {
            'fields': ('notify_match_found', 'notify_report_status', 'notify_verification', 
                       'notify_system', 'notify_admin')
        }),
        ('إعدادات أخرى', {
            'fields': ('min_priority', 'quiet_hours_start', 'quiet_hours_end')
        }),
    )