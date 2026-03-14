from rest_framework import permissions


class IsVerifiedUser(permissions.BasePermission):
    """
    صلاحية: يسمح بالوصول فقط للمستخدمين الذين تم التحقق من هويتهم.
    - المشرفون يمكنهم الوصول دائماً
    - المستخدمون العاديون يحتاجون إلى توثيق الهوية
    """
    
    def has_permission(self, request, view):
        # التحقق من تسجيل الدخول
        if not (request.user and request.user.is_authenticated):
            return False
        
        # المشرفون يمكنهم الوصول دائماً
        if request.user.is_admin():
            return True
        
        # المستخدمون العاديون يحتاجون إلى توثيق الهوية
        return request.user.verification_status == 'verified'


class IsVolunteerOrHigher(permissions.BasePermission):
    """
    صلاحية: يسمح بالوصول للمتطوعين والمشرفين فقط.
    - المتطوعون والمشرفون ومديرو النظام
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        return request.user.is_volunteer_or_higher()
    
    def has_object_permission(self, request, view, obj):
        """التحقق من صلاحية الوصول لكائن معين"""
        if not (request.user and request.user.is_authenticated):
            return False
        
        # المشرفون يمكنهم الوصول لأي كائن
        if request.user.is_admin():
            return True
        
        # المتطوعون يمكنهم الوصول إذا كانوا يمتلكون الكائن
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        return False


class IsAdminUser(permissions.BasePermission):
    """
    صلاحية: يسمح بالوصول للمشرفين فقط.
    - المشرفون ومديرو النظام
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        return request.user.is_admin()
    
    def has_object_permission(self, request, view, obj):
        """المشرفون يمكنهم الوصول لأي كائن"""
        return self.has_permission(request, view)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    صلاحية: المالك فقط يمكنه التعديل، والجميع يمكنهم القراءة.
    - المشرفون يمكنهم تعديل أي شيء
    """
    
    def has_object_permission(self, request, view, obj):
        # السماح بقراءة للجميع
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # المشرفون يمكنهم فعل أي شيء
        if request.user and request.user.is_admin():
            return True
        
        # التحقق من الملكية
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False


class IsSelf(permissions.BasePermission):
    """
    صلاحية: المستخدم يمكنه الوصول فقط لبياناته الشخصية.
    - المشرفون يمكنهم الوصول للجميع
    """
    
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # المشرفون يمكنهم الوصول للجميع
        if request.user.is_admin():
            return True
        
        # المستخدم العادي يمكنه الوصول فقط لنفسه
        return obj == request.user