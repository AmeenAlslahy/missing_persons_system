from .models import AuditLog
import logging
from django.utils import timezone
import json

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def get_client_ip(request):
        """الحصول على عنوان IP الحقيقي"""
        if not request:
            return None
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        
        return request.META.get('REMOTE_ADDR')
    
    @staticmethod
    def get_client_info(request):
        """الحصول على معلومات العميل"""
        if not request:
            return {'ip': None, 'user_agent': ''}
        
        return {
            'ip': AuditService.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],  # تحديد الطول
            'referer': request.META.get('HTTP_REFERER', ''),
        }
    
    @staticmethod
    def log_action(user, action, resource_type, resource_id='', data_before=None, data_after=None, request=None, **extra):
        """تسجيل عملية في نظام المراجعة"""
        try:
            client_info = AuditService.get_client_info(request)
            
            # تنظيف البيانات لتجنب الأخطاء
            if data_before and not isinstance(data_before, dict):
                try:
                    data_before = {'value': str(data_before)}
                except:
                    data_before = None
            
            if data_after and not isinstance(data_after, dict):
                try:
                    data_after = {'value': str(data_after)}
                except:
                    data_after = None
            
            # إنشاء سجل المراجعة
            log_entry = AuditLog.objects.create(
                user=user if user and user.is_authenticated else None,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id)[:100],  # تحديد الطول
                data_before=data_before,
                data_after=data_after,
                ip_address=client_info['ip'],
                user_agent=client_info['user_agent'],
                timestamp=timezone.now()
            )
            
            # إضافة أي بيانات إضافية
            if extra:
                logger.debug(f"Extra audit data: {extra}")
            
            return log_entry
            
        except Exception as e:
            logger.error(f"Error creating audit log: {e}", exc_info=True)
            return None
    
    @staticmethod
    def log_login(user, request, success=True):
        """تسجيل محاولة دخول"""
        return AuditService.log_action(
            user=user if success else None,
            action='LOGIN',
            resource_type='Auth',
            resource_id=user.phone if user else 'unknown',
            data_after={'success': success},
            request=request
        )
    
    @staticmethod
    def log_logout(user, request):
        """تسجيل خروج"""
        return AuditService.log_action(
            user=user,
            action='LOGOUT',
            resource_type='Auth',
            resource_id=user.phone,
            request=request
        )
    
    @staticmethod
    def get_user_audit_logs(user, limit=50):
        """الحصول على سجل عمليات مستخدم معين"""
        return AuditLog.objects.filter(user=user).select_related('user')[:limit]
    
    @staticmethod
    def get_resource_audit_logs(resource_type, resource_id, limit=50):
        """الحصول على سجل عمليات مورد معين"""
        return AuditLog.objects.filter(
            resource_type=resource_type,
            resource_id=str(resource_id)
        ).select_related('user')[:limit]