from rest_framework import serializers
from .models import AuditLog
from accounts.models import User


class UserMinimalSerializer(serializers.ModelSerializer):
    """سرياليزر مبسط للمستخدم"""
    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name']


class AuditLogSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True, default='النظام')
    user_details = UserMinimalSerializer(source='user', read_only=True)
    created_at = serializers.DateTimeField(source='timestamp', read_only=True)
    action_type = serializers.CharField(source='action', read_only=True)
    action_display = serializers.SerializerMethodField()
    action_details = serializers.SerializerMethodField()
    formatted_data = serializers.SerializerMethodField()
    ip_address = serializers.ReadOnlyField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_details', 'user_full_name', 
            'action_type', 'action_display', 'action_details',
            'resource_type', 'resource_id',
            'formatted_data', 'ip_address', 'user_agent', 'created_at'
        ]
    
    def get_action_display(self, obj):
        """الحصول على التسمية العربية للعملية"""
        return obj.get_action_display()
    
    def get_action_details(self, obj):
        """تفاصيل مبسطة للعملية"""
        if obj.resource_id:
            return f'{obj.get_action_display()} لـ {obj.resource_type} ({obj.resource_id})'
        return f'{obj.get_action_display()} لـ {obj.resource_type}'
    
    def get_formatted_data(self, obj):
        """تنسيق البيانات للتقديم"""
        data = {}
        if obj.data_before:
            data['before'] = obj.data_before
        if obj.data_after:
            data['after'] = obj.data_after
        return data if data else None