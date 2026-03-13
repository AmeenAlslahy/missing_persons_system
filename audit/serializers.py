from rest_framework import serializers
from .models import AuditLog
from accounts.models import User

class AuditLogSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True, default='النظام')
    created_at = serializers.DateTimeField(source='timestamp', read_only=True)
    action_type = serializers.CharField(source='action', read_only=True)
    action_details = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_full_name', 'action_type', 'action_details', 'ip_address', 'user_agent', 'created_at']

    def get_action_details(self, obj):
        details = f'{obj.get_action_display()} لـ {obj.resource_type} ({obj.resource_id})'
        if obj.data_after:
            details += f' - التفاصيل: {str(obj.data_after)[:100]}'
        return details
