import threading
from django.utils import timezone
from .services import AuditService
import logging

logger = logging.getLogger(__name__)

class AuditLogMiddleware:
    """Middleware لتسجيل معلومات الطلبات"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # تخزين وقت البداية
        request.start_time = timezone.now()
        
        # تخزين معلومات العميل
        request.auditlog_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            'path': request.path,
            'method': request.method,
            'timestamp': timezone.now(),
        }
        
        response = self.get_response(request)
        
        # تسجيل الطلبات المهمة (POST, PUT, DELETE)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and request.user.is_authenticated:
            self.log_request(request, response)
        
        return response
    
    def get_client_ip(self, request):
        """الحصول على عنوان IP الحقيقي"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def log_request(self, request, response):
        """تسجيل الطلب"""
        try:
            # تجنب تسجيل الطلبات الكبيرة جداً
            if len(request.path) > 100:
                return
            
            # تسجيل فقط للعمليات المهمة
            if response.status_code < 400:  # نجاح
                AuditService.log_action(
                    user=request.user,
                    action=request.method,
                    resource_type=request.path.split('/')[1] if '/' in request.path else 'unknown',
                    resource_id=request.path.split('/')[-1] if '/' in request.path else '',
                    data_after={'status': response.status_code},
                    request=request
                )
        except Exception as e:
            logger.error(f"Error in audit middleware: {e}")