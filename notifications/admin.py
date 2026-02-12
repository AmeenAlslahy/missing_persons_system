from django.contrib import admin
from django.utils.html import format_html
from .models import Notification, NotificationPreference, NotificationTemplate, PushNotificationToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'user', 'title', 'notification_type', 
                   'priority_level', 'is_read', 'is_sent', 'created_at']
    list_filter = ['notification_type', 'priority_level', 'is_read', 'is_sent', 'created_at']
    search_fields = ['user__email', 'user__full_name', 'title', 'message']
    readonly_fields = ['notification_id', 'created_at', 'sent_at', 'read_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('notification_id', 'user', 'notification_type', 'title', 'message')
        }),
        ('الأولوية والحالة', {
            'fields': ('priority_level', 'is_read', 'is_sent', 'delivery_method')
        }),
        ('الارتباطات', {
            'fields': ('related_report', 'related_match')
        }),
        ('الإجراءات', {
            'fields': ('action_required', 'action_url', 'action_text')
        }),
        ('الصلاحية', {
            'fields': ('expires_at',)
        }),
        ('بيانات إضافية', {
            'fields': ('metadata',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'sent_at', 'read_at')
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'resend_notifications']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"تم تحديد {queryset.count()} إشعار كمقروء")
    mark_as_read.short_description = "تعيين كمقروء"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"تم تحديد {queryset.count()} إشعار كغير مقروء")
    mark_as_unread.short_description = "تعيين كغير مقروء"
    
    def resend_notifications(self, request, queryset):
        # هنا يمكن إضافة منطق إعادة الإرسال
        self.message_user(request, f"سيتم إعادة إرسال {queryset.count()} إشعار")
    resend_notifications.short_description = "إعادة إرسال"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'receive_push_notifications', 'receive_email_notifications', 
                   'quiet_hours_enabled', 'updated_at']
    list_filter = ['receive_push_notifications', 'receive_email_notifications', 
                  'quiet_hours_enabled', 'preferred_language']
    search_fields = ['user__email', 'user__full_name']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('المستخدم', {
            'fields': ('user',)
        }),
        ('تفضيلات أنواع الإشعارات', {
            'fields': ('enable_match_notifications', 'enable_report_updates', 
                      'enable_admin_messages', 'enable_system_updates',
                      'enable_urgent_alerts', 'enable_volunteer_alerts')
        }),
        ('تفضيلات طريقة التوصيل', {
            'fields': ('receive_push_notifications', 'receive_email_notifications', 
                      'receive_sms_notifications')
        }),
        ('ساعات الهدوء', {
            'fields': ('quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end')
        }),
        ('تفضيلات أخرى', {
            'fields': ('preferred_language', 'app_update_frequency')
        }),
    )


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_name', 'notification_type', 'default_priority', 
                   'is_active', 'updated_at']
    list_filter = ['notification_type', 'default_priority', 'is_active']
    search_fields = ['template_name', 'title_ar', 'title_en']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('template_name', 'notification_type', 'is_active')
        }),
        ('المحتوى العربي', {
            'fields': ('title_ar', 'message_ar', 'default_action_text_ar')
        }),
        ('المحتوى الإنجليزي', {
            'fields': ('title_en', 'message_en', 'default_action_text_en')
        }),
        ('المتغيرات', {
            'fields': ('variables',)
        }),
        ('الإجراءات', {
            'fields': ('default_action_url',)
        }),
        ('الإعدادات', {
            'fields': ('default_priority', 'default_expiry_days')
        }),
    )
    
    actions = ['activate_templates', 'deactivate_templates']
    
    def activate_templates(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"تم تفعيل {queryset.count()} قالب")
    activate_templates.short_description = "تفعيل القوالب"
    
    def deactivate_templates(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"تم تعطيل {queryset.count()} قالب")
    deactivate_templates.short_description = "تعطيل القوالب"


@admin.register(PushNotificationToken)
class PushNotificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'device_name', 'app_version', 
                   'is_active', 'last_active']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['user__email', 'device_token', 'device_name']
    readonly_fields = ['created_at', 'last_active']
    
    def has_add_permission(self, request):
        return False