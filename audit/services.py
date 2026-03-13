from .models import AuditLog
import logging

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def log_action(user, action, resource_type, resource_id='', data_before=None, data_after=None, request=None):
        """تسجيل عملية في نظام المراجعة"""
        try:
            ip_address = None
            user_agent = ''
            
            if request:
                # محاولة الحصول على عنوان IP الحقيقي إذا كان خلف بروكسي
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')

            AuditLog.objects.create(
                user=user if user and user.is_authenticated else None,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                data_before=data_before,
                data_after=data_after,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
