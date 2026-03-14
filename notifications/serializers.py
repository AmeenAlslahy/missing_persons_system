from rest_framework import serializers
from django.utils import timezone
from django.utils.timesince import timesince
from django.utils.translation import gettext_lazy as _
from .models import Notification, NotificationPreference


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """سرياليزر لتفضيلات الإشعارات"""
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'sms_enabled', 'push_enabled',
            'notify_match_found', 'notify_report_status', 
            'notify_verification', 'notify_system', 'notify_admin',
            'min_priority', 'quiet_hours_start', 'quiet_hours_end'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """سرياليزر للإشعارات"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_level_display = serializers.CharField(source='get_priority_level_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'notification_id', 'title', 'message', 
            'notification_type', 'notification_type_display',
            'priority_level', 'priority_level_display',
            'is_read', 'read_at', 'created_at', 'expires_at',
            'action_required', 'action_url', 'action_text',
            'related_report', 'related_match', 'metadata',
            'time_ago'
        ]
        read_only_fields = ['notification_id', 'created_at', 'read_at']
    
    def get_time_ago(self, obj):
        """حساب الوقت المنقضي منذ الإنشاء"""
        if obj.created_at:
            time_diff = timesince(obj.created_at, timezone.now())
            return f"منذ {time_diff}"
        return ""
    
    def to_representation(self, instance):
        """تعديل عرض البيانات"""
        data = super().to_representation(instance)
        
        # إضافة معلومات البلاغ إذا كان موجوداً
        if instance.related_report:
            data['related_report'] = {
                'id': str(instance.related_report.report_id),
                'code': instance.related_report.report_code,
                'person_name': str(instance.related_report.person) if instance.related_report.person else None
            }
            # إزالة الـ ID الخام
            data.pop('related_report', None)
        
        # إضافة معلومات المطابقة إذا كانت موجودة
        if instance.related_match:
            data['related_match'] = {
                'id': str(instance.related_match.match_id),
                'similarity_score': getattr(instance.related_match, 'similarity_score', None)
            }
            data.pop('related_match', None)
        
        return data


class NotificationCreateSerializer(serializers.Serializer):
    """سرياليزر لإنشاء إشعارات (للمشرفين)"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text='قائمة بمعرفات المستخدمين (إذا تركت فارغة، ترسل للجميع)'
    )
    notification_type = serializers.ChoiceField(
        choices=[t[0] for t in Notification.NOTIFICATION_TYPES],
        required=True
    )
    title = serializers.CharField(max_length=255, required=True)
    message = serializers.CharField(required=True)
    priority_level = serializers.ChoiceField(
        choices=[p[0] for p in Notification.PRIORITY_LEVELS],
        default='normal'
    )
    action_required = serializers.BooleanField(default=False)
    action_url = serializers.URLField(required=False, allow_blank=True)
    action_text = serializers.CharField(max_length=100, required=False, allow_blank=True)
    expiry_days = serializers.IntegerField(min_value=1, max_value=365, default=7)
    
    def validate(self, data):
        """التحقق من صحة البيانات"""
        if data.get('action_required') and not data.get('action_url'):
            raise serializers.ValidationError({
                'action_url': _('مطلوب رابط الإجراء عندما يكون الإشعار يتطلب إجراء')
            })
        
        if data.get('action_required') and not data.get('action_text'):
            data['action_text'] = _('عرض التفاصيل')
        
        return data


class NotificationStatsSerializer(serializers.Serializer):
    """سرياليزر لإحصائيات الإشعارات"""
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    urgent_notifications = serializers.IntegerField()
    by_type = serializers.DictField(child=serializers.IntegerField())
    by_day = serializers.ListField(child=serializers.DictField())


class MarkAsReadSerializer(serializers.Serializer):
    """سرياليزر لتحديد الإشعارات كمقروءة"""
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    read_all = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """التحقق من البيانات"""
        if not data.get('read_all') and not data.get('notification_ids'):
            raise serializers.ValidationError({
                'notification_ids': _('مطلوب على الأقل معرف إشعار واحد أو تحديد read_all')
            })
        
        return data