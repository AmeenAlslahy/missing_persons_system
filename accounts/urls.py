from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    # المصادقة
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # الملف الشخصي
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/update/', views.UserUpdateView.as_view(), name='profile-update'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password-change'),
    
    # التحقق عبر OTP
    path('otp/send/', views.SendOTPView.as_view(), name='otp-send'),
    path('otp/verify/', views.VerifyOTPView.as_view(), name='otp-verify'),
    path('verify/request/', views.VerificationRequestView.as_view(), name='verification-request'),
    
    # API endpoints (مضمنة في router)
    path('', include(router.urls)),
]

# إضافة أسماء مسارات واضحة للتوجيه العكسي
app_name = 'accounts'