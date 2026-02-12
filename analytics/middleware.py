import time
from django.utils import timezone
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class AnalyticsMiddleware:
    """ميدل وير لتتبع وتحليل الطلبات"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # تسجيل وقت البدء
        start_time = time.time()
        
        # تنفيذ الطلب
        response = self.get_response(request)
        
        # حساب وقت المعالجة
        processing_time = time.time() - start_time
        
        # تسجيل الطلب (فقط للطلبات المهمة)
        if self._should_track_request(request):
            self._log_request(request, response, processing_time)
        
        # إضافة معلومات الأداء للرأس
        response['X-Processing-Time'] = f'{processing_time:.3f}s'
        
        return response
    
    def _should_track_request(self, request):
        """تحديد إذا كان يجب تتبع الطلب"""
        # تجاهل طلبات الإدارة
        if request.path.startswith('/admin/'):
            return False
        
        # تجاهل طلبات الملفات الثابتة
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return False
        
        # تجاهل طلبات API البسيطة (GET)
        if request.method == 'GET' and not request.path.startswith('/api/'):
            return False
        
        return True
    
    def _log_request(self, request, response, processing_time):
        """تسجيل معلومات الطلب"""
        try:
            from .models import RequestLog
            
            # تجميع معلومات الطلب
            user = request.user if request.user.is_authenticated else None
            
            log_data = {
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'processing_time': processing_time,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'ip_address': self._get_client_ip(request),
                'query_params': dict(request.GET),
                'user_id': user.id if user else None,
                'response_size': len(response.content) if hasattr(response, 'content') else 0,
            }
            
            # تسجيل الاستعلامات إذا كانت بطيئة
            if processing_time > 1.0:  # أكثر من ثانية
                log_data['slow_queries'] = self._get_slow_queries()
            
            # حفظ في قاعدة البيانات (يمكن تعطيله في الإنتاج للكفاءة)
            # RequestLog.objects.create(**log_data)
            
            # تسجيل في الـ logs
            logger.info(
                f"Request: {request.method} {request.path} "
                f"({processing_time:.3f}s, {response.status_code})"
            )
            
        except Exception as e:
            logger.error(f"Error logging request: {e}")
    
    def _get_client_ip(self, request):
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_slow_queries(self):
        """الحصول على الاستعلامات البطيئة"""
        slow_queries = []
        for query in connection.queries:
            if float(query.get('time', 0)) > 0.1:  # أكثر من 0.1 ثانية
                slow_queries.append({
                    'sql': query.get('sql', '')[:500],
                    'time': query.get('time', 0),
                })
        return slow_queries