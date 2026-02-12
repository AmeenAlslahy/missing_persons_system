from rest_framework import generics, status, permissions, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import logout
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from .models import User, VolunteerProfile, AuditLog
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, 
    UserProfileSerializer, UserUpdateSerializer,
    VolunteerProfileSerializer, PasswordChangeSerializer,
    AuditLogSerializer, UserAdminActionSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """تسجيل مستخدم جديد"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # إنشاء توكنات JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': _('تم إنشاء الحساب بنجاح')
        }, status=status.HTTP_201_CREATED)


class UserLoginView(TokenObtainPairView):
    """تسجيل الدخول"""
    serializer_class = UserLoginSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # تحديث آخر دخول
        user.update_last_login()
        
        # إنشاء توكنات
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': _('تم تسجيل الدخول بنجاح')
        })


class UserLogoutView(APIView):
    """تسجيل الخروج"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logout(request)
            
            # تسجيل في سجل التدقيق
            request.user.audit_logs.create(
                action_type='LOGOUT',
                action_details='تسجيل الخروج',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': _('تم تسجيل الخروج بنجاح')
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserProfileView(generics.RetrieveUpdateAPIView):
    """عرض وتحديث الملف الشخصي"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserUpdateView(generics.UpdateAPIView):
    """تحديث بيانات المستخدم"""
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.UpdateAPIView):
    """تغيير كلمة المرور"""
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': _('تم تغيير كلمة المرور بنجاح')
        }, status=status.HTTP_200_OK)


class VolunteerListView(generics.ListAPIView):
    """قائمة المتطوعين"""
    serializer_class = VolunteerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # إرجاع المتطوعين النشطين فقط
        return VolunteerProfile.objects.filter(
            user__user_role__in=['volunteer', 'admin', 'super_admin'],
            is_active_volunteer=True
        ).select_related('user')


class VolunteerDetailView(generics.RetrieveAPIView):
    """تفاصيل متطوع"""
    serializer_class = VolunteerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return VolunteerProfile.objects.all().select_related('user')


class VerificationRequestView(APIView):
    """طلب التحقق من الهوية"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.verification_status != User.VerificationStatus.PENDING:
            return Response({
                'error': _('لقد قمت بالفعل بطلب التحقق')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        national_id = request.data.get('national_id')
        if not national_id:
            return Response({
                'error': _('يجب إدخال رقم الهوية الوطنية')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # هنا يمكن إضافة تحقق من صحة الرقم الوطني
        
        user.national_id = national_id
        user.verification_status = User.VerificationStatus.PENDING
        user.save()
        
        # تسجيل في سجل التدقيق
        user.audit_logs.create(
            action_type='VERIFICATION_REQUEST',
            action_details=f'طلب التحقق برقم الهوية: {national_id}'
        )
        
        # هنا يمكن إرسال إشعار للمشرفين
        
        return Response({
            'message': _('تم إرسال طلب التحقق بنجاح، سيتم مراجعته من قبل المشرفين')
        }, status=status.HTTP_200_OK)


class AdminVerifyUserView(APIView):
    """تحقق المشرف من مستخدم"""
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': _('المستخدم غير موجود')
            }, status=status.HTTP_404_NOT_FOUND)
        
        action = request.data.get('action')  # accept أو reject
        notes = request.data.get('notes', '')
        
        if action == 'accept':
            user.verification_status = User.VerificationStatus.VERIFIED
            
            # إذا كان لديه صورة شخصية، يمكن تحويله لمتطوع
            if user.profile_picture and user.user_role == User.Role.USER:
                user.user_role = User.Role.VOLUNTEER
                VolunteerProfile.objects.get_or_create(user=user)
            
            message = _('تم التحقق من المستخدم بنجاح')
        elif action == 'reject':
            user.verification_status = User.VerificationStatus.REJECTED
            message = _('تم رفض طلب التحقق')
        else:
            return Response({
                'error': _('الإجراء غير صالح')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.save()
        
        # تسجيل في سجل التدقيق
        AuditLog.objects.create(
            user=request.user,
            action_type=f'VERIFICATION_{action.upper()}',
            action_details=f'تحقق من المستخدم {user.email}: {notes}',
            ip_address=self.get_client_ip(request)
        )
        
        # إرسال إشعار للمستخدم
        # TODO: إرسال إشعار
        
        return Response({
            'message': message,
            'user': UserProfileSerializer(user).data
        })
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet للمستخدمين (للمشرفين)"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['verification_status', 'user_role', 'gender', 'is_active', 'is_blocked']
    search_fields = ['email', 'full_name', 'phone', 'national_id', 'governorate', 'district']
    ordering_fields = ['date_joined', 'last_login', 'trust_score']

    @action(detail=True, methods=['post'])
    def admin_action(self, request, pk=None):
        """إجراءات المشرف: حظر، فك حظر، توثيق، تغيير دور، تحديث ثقة"""
        user = self.get_object()
        serializer = UserAdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        new_role = serializer.validated_data.get('new_role', '')
        
        if action_type == 'block':
            user.is_blocked = True
            user.blocking_reason = reason
            user.is_active = False
            msg = _('تم حظر المستخدم بنجاح')
        elif action_type == 'unblock':
            user.is_blocked = False
            user.blocking_reason = None
            user.is_active = True
            msg = _('تم رفع الحظر عن المستخدم بنجاح')
        elif action_type == 'verify':
            user.verification_status = User.VerificationStatus.VERIFIED
            msg = _('تم توثيق حساب المستخدم')
        elif action_type == 'reject_verification':
            user.verification_status = User.VerificationStatus.REJECTED
            msg = _('تم رفض توثيق حساب المستخدم')
        elif action_type == 'change_role':
            if new_role in [r[0] for r in User.Role.choices]:
                user.user_role = new_role
                msg = _(f'تم تغيير دور المستخدم إلى {user.get_user_role_display()}')
            else:
                return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
        elif action_type == 'recalculate_trust':
            user.update_trust_score()
            msg = _(f'تم تحديث درجة الثقة: {user.trust_score:.1f}%')
            
        user.save()
        
        # تسجيل في سجل التدقيق
        AuditLog.objects.create(
            user=request.user,
            action_type=f'ADMIN_{action_type.upper()}',
            action_details=f'إجراء {action_type} على {user.email}. السبب: {reason}',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'message': msg, 'user': UserProfileSerializer(user).data})

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet لسجلات التدقيق (للمشرفين)"""
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user', 'action_type']
    search_fields = ['action_details', 'user__full_name', 'user__email', 'ip_address']
