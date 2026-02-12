from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

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
    
    # التحقق
    path('verify/request/', views.VerificationRequestView.as_view(), name='verification-request'),
    
    # المتطوعون
    path('volunteers/', views.VolunteerListView.as_view(), name='volunteers-list'),
    path('volunteers/<int:id>/', views.VolunteerDetailView.as_view(), name='volunteer-detail'),
    
    # إدارية (للمشرفين فقط)
    path('admin/verify/<int:user_id>/', views.AdminVerifyUserView.as_view(), name='admin-verify'),
    path('users/', views.UserViewSet.as_view({'get': 'list'}), name='user-list'),
    path('audit-logs/', views.AuditLogViewSet.as_view({'get': 'list'}), name='audit-log-list'),
]