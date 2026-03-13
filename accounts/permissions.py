from rest_framework import permissions

class IsVerifiedUser(permissions.BasePermission):
    """
    يسمح بالوصول فقط للمستخدمين الذين تم التحقق من هويتهم.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.is_staff or request.user.verification_status == 'verified'

class IsVolunteerOrHigher(permissions.BasePermission):
    """
    يسمح بالوصول للمتطوعين والمشرفين فقط.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
            
        allowed_roles = ['volunteer', 'admin', 'super_admin']
        return hasattr(request.user, 'role') and request.user.role in allowed_roles

class IsAdminUser(permissions.BasePermission):
    """
    يسمح بالوصول للمشرفين فقط.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
            
        allowed_roles = ['admin', 'super_admin']
        return hasattr(request.user, 'role') and request.user.role in allowed_roles
