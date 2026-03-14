from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    صلاحية مخصصة: - السماح للمالك فقط بالتعديل
                   - المشرفين يمكنهم تعديل أي شيء
                   - الجميع يمكنهم القراءة
    """
    
    def has_object_permission(self, request, view, obj):
        # السماح بقراءة للجميع
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # المشرفين يمكنهم فعل أي شيء
        if request.user and request.user.is_staff:
            return True
        
        # التحقق من الملكية (افترض أن المستخدم مخزن في obj.user)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsVerifiedUser(permissions.BasePermission):
    """
    صلاحية للتحقق من أن المستخدم موثق
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and getattr(request.user, 'is_verified', False)