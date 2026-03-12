from .models import User

def user_profile(request):
    """Context processor لإضافة بيانات المستخدم للقوالب"""
    if request.user.is_authenticated:
        return {
            'user': request.user,
            'user_full_name': request.user.full_name,
            'user_type_display': request.user.get_user_type_display(),
        }
    return {}