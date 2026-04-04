import logging
from audit.models import AuditLog
from utils.helpers import get_client_ip

logger = logging.getLogger(__name__)

class ErrorLoggingMiddleware:
    """تسجيل جميع الأخطاء المرتبطة بـ API في سجل العمليات (AuditLog)"""
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # تسجيل الأخطاء (400 فما فوق) في سجل العمليات
        if response.status_code >= 400:
            try:
                # محاولة الحصول على كود الخطأ إن وجد في الرد الموحد
                error_code = None
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    error_code = response.data.get('error_code')
                
                # تسجيل العملية كخطأ
                AuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='STATUS_CHANGE',  # Or a custom action if needed, but STATUS_CHANGE exists
                    resource_type='API_ERROR',
                    resource_id=str(response.status_code),
                    data_after={
                        'error_code': error_code,
                        'path': request.path,
                        'method': request.method,
                        'status_code': response.status_code
                    },
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
            except Exception as e:
                logger.error(f"Error in ErrorLoggingMiddleware: {e}")
        
        return response
