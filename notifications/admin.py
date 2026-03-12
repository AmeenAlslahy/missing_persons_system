from django.contrib import admin
from .models import Notification
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
            'fields': ('priority_level', 'is_read')
        }),
        ('الارتباطات', {
            'fields': ('report_1', 'report_2')
        }),
        ('الصلاحية', {
            'fields': ('expires_at',)
        }),
        ('التواريخ', {
            'fields': ('created_at',)
        }),
    )