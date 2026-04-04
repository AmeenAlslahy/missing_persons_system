# utils/error_codes.py

ERROR_CODES = {
    # Auth errors (AUTH_xxx)
    'AUTH_001': ('رقم الهاتف أو كلمة المرور غير صحيحة', 'Invalid phone or password'),
    'AUTH_002': ('ليس لديك صلاحية للوصول إلى هذا المورد', 'Insufficient permissions'),
    'AUTH_003': ('جلسة الدخول منتهية، الرجاء تسجيل الدخول مرة أخرى', 'Session expired'),
    
    # Validation errors (VALIDATION_xxx)
    'VALIDATION_001': ('بيانات غير صالحة', 'Invalid data provided'),
    
    # OTP errors (OTP_xxx)
    'OTP_001': ('رمز التحقق غير صحيح أو منتهي الصلاحية', 'Invalid or expired OTP code'),
    'OTP_002': ('لقد تجاوزت الحد المسموح لمحاولات التحقق', 'Too many OTP attempts'),
    'OTP_003': ('لقد تجاوزت الحد المسموح لطلبات OTP', 'Too many OTP requests'),
    
    # Report errors (REPORT_xxx)
    'REPORT_001': ('يوجد بلاغ نشط لهذا الشخص بالفعل', 'Active report already exists for this person'),
    'REPORT_002': ('لا يمكن تعديل بلاغ تم حله', 'Cannot modify resolved report'),
    'REPORT_003': ('لا يمكن حذف بلاغ مرتبط بمطابقات نشطة', 'Cannot delete report with active matches'),
    
    # Not found errors (NOTFOUND_xxx)
    'NOTFOUND_001': ('المورد المطلوب غير موجود', 'Requested resource not found'),
    'NOTFOUND_002': ('المستخدم غير موجود', 'User not found'),
    'NOTFOUND_003': ('البلاغ غير موجود', 'Report not found'),
    
    # Rate limit errors (RATE_xxx)
    'RATE_001': ('عدد الطلبات كبير جداً، الرجاء المحاولة لاحقاً', 'Too many requests, please try again later'),
    
    # Server errors (SERVER_xxx)
    'SERVER_001': ('حدث خطأ داخلي في الخادم، الرجاء المحاولة لاحقاً', 'Internal server error, please try again later'),
}
