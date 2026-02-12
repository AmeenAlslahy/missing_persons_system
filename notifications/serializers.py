from rest_framework import serializers
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Notification, NotificationPreference, NotificationTemplate, PushNotificationToken


class NotificationSerializer(serializers.ModelSerializer):
    """سرياليزر للإشعارات"""
    notification_type_display = serializers.ReadOnlyField(source='get_notification_type_display')
    priority_level_display = serializers.ReadOnlyField(source='get_priority_level_display')
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'notification_id', 'title', 'message', 'notification_type', 
            'notification_type_display', 'priority_level', 'priority_level_display',
            'action_required', 'action_url', 'action_text',
            'is_read', 'is_sent', 'created_at', 'read_at', 'expires_at',
            'related_report_id', 'related_match_id', 'time_ago'
        ]
        read_only_fields = ['notification_id', 'created_at', 'read_at', 'expires_at']
    
    def get_time_ago(self, obj):
        """حساب الوقت المنقضي منذ الإنشاء"""
        from django.utils.timesince import timesince
        
        now = timezone.now()
        if obj.created_at:
            time_diff = timesince(obj.created_at, now)
            return f"منذ {time_diff}"
        return ""
    
    def to_representation(self, instance):
        """تعديل عرض البيانات"""
        data = super().to_representation(instance)
        
        # إضافة رابط البلاغ إذا كان موجوداً
        if instance.related_report:
            data['related_report'] = {
                'id': str(instance.related_report.report_id),
                'code': instance.related_report.report_code,
                'person_name': instance.related_report.person_name
            }
        
        # إضافة رابط المطابقة إذا كانت موجودة
        if instance.related_match:
            data['related_match'] = {
                'id': str(instance.related_match.match_id),
                'similarity_score': instance.related_match.similarity_score
            }
        
        return data


class NotificationCreateSerializer(serializers.Serializer):
    """سرياليزر لإنشاء إشعارات (للمشرفين)"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='قائمة بمعرفات المستخدمين (إذا فارغة، ترسل للجميع)'
    )
    notification_type = serializers.ChoiceField(
        choices=Notification.NotificationType.choices,
        required=True
    )
    title = serializers.CharField(max_length=255, required=True)
    message = serializers.CharField(required=True)
    priority_level = serializers.ChoiceField(
        choices=Notification.PriorityLevel.choices,
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
        
        return data


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """سرياليزر لتفضيلات الإشعارات"""
    user_email = serializers.ReadOnlyField(source='user.email')
    user_full_name = serializers.ReadOnlyField(source='user.full_name')
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'user_email', 'user_full_name',
            'enable_match_notifications', 'enable_report_updates',
            'enable_admin_messages', 'enable_system_updates',
            'enable_urgent_alerts', 'enable_volunteer_alerts',
            'receive_push_notifications', 'receive_email_notifications',
            'receive_sms_notifications', 'quiet_hours_enabled',
            'quiet_hours_start', 'quiet_hours_end',
            'preferred_language', 'app_update_frequency',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'updated_at']
    
    def validate(self, data):
        """التحقق من ساعات الهدوء"""
        if data.get('quiet_hours_enabled', self.instance.quiet_hours_enabled if self.instance else False):
            start = data.get('quiet_hours_start', self.instance.quiet_hours_start if self.instance else '22:00')
            end = data.get('quiet_hours_end', self.instance.quiet_hours_end if self.instance else '07:00')
            
            if start == end:
                raise serializers.ValidationError({
                    'quiet_hours_start': _('يجب أن تكون ساعات البداية والنهاية مختلفة'),
                    'quiet_hours_end': _('يجب أن تكون ساعات البداية والنهاية مختلفة')
                })
        
        return data


class PushNotificationTokenSerializer(serializers.ModelSerializer):
    """سرياليزر لرموز الإشعارات الدفعية"""
    class Meta:
        model = PushNotificationToken
        fields = ['id', 'device_token', 'device_type', 'device_name', 
                 'device_model', 'app_version', 'os_version', 'is_active']
        read_only_fields = ['id', 'user']
    
    def create(self, validated_data):
        """إنشاء أو تحديث رمز الجهاز"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        # إذا كان الرمز موجوداً للمستخدم، نقوم بالتحديث
        device_token = validated_data.get('device_token')
        if device_token and 'user' in validated_data:
            instance, created = PushNotificationToken.objects.update_or_create(
                device_token=device_token,
                user=validated_data['user'],
                defaults=validated_data
            )
            return instance
        
        return super().create(validated_data)


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
        required=True
    )
    read_all = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """التحقق من البيانات"""
        if not data.get('read_all') and not data.get('notification_ids'):
            raise serializers.ValidationError({
                'notification_ids': _('مطلوب على الأقل معرف إشعار واحد')
            })
        
        return data