import logging
from datetime import datetime
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, PermissionDenied, NotFound, Throttled
from utils.error_codes import ERROR_CODES

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        error_code = get_error_code(exc, response)
        message_ar, message_en = ERROR_CODES.get(error_code, ('حدث خطأ ما', 'An error occurred'))
        
        # Override message based on DRF specific detail if it's validation error or similar
        # but the user requested setting Arabic and English messages explicitly from ERROR_CODES
        # so we will rely on ERROR_CODES mostly, but keep original details.

        response.data = {
            'success': False,
            'error_code': error_code,
            'message': message_ar,
            'message_en': message_en,
            'details': extract_details(response.data),
            'timestamp': datetime.now().isoformat()
        }
        
        # إضافة معلومات إضافية حسب نوع الخطأ
        if isinstance(exc, Throttled):
            response.data['retry_after_seconds'] = getattr(exc, 'wait', 60)
        elif isinstance(exc, AuthenticationFailed):
            # For simplicity, we might not always have context or remaining attempts easily available 
            # without custom throttling tracking, but we'll try fetching it if injected via views.
            request = context.get('request')
            if request and hasattr(request, 'remaining_attempts'):
                response.data['remaining_attempts'] = getattr(request, 'remaining_attempts', 0)
    
    return response

def get_error_code(exc, response):
    if isinstance(exc, ValidationError):
        return 'VALIDATION_001'
    if isinstance(exc, AuthenticationFailed):
        return 'AUTH_001'
    if isinstance(exc, PermissionDenied):
        return 'AUTH_002'
    if isinstance(exc, NotFound):
        return 'NOTFOUND_001'
    if isinstance(exc, Throttled):
        # We can distinguish OTP throttled vs Login throttled if needed by inspecting exc
        # but RATE_001 is the default general
        return 'RATE_001'
    return 'SERVER_001'

def extract_details(data):
    """استخراج تفاصيل الخطأ من رد DRF"""
    if isinstance(data, dict):
        # تجاهل الحقول التي تمت معالجتها بالفعل
        details = {k: v for k, v in data.items() if k not in ['detail', 'non_field_errors']}
        return details if details else None
    elif isinstance(data, list):
        return {"errors": data}
    return None
