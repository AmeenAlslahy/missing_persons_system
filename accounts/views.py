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
import random
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.conf import settings
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
import logging

from .models import User
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    UserProfileSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, UserAdminSerializer
)

logger = logging.getLogger(__name__)

# Rate limiter مخصص لـ OTP
class OTPRateThrottle(UserRateThrottle):
    rate = '3/hour'  # 3 محاولات في الساعة


class UserRegistrationView(generics.CreateAPIView):
    """تسجيل مستخدم جديد مع تحسينات"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            refresh = RefreshToken.for_user(user)
            
            logger.info(f"New user registered: {user.phone}")

            return Response({
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': _('تم إنشاء الحساب بنجاح')
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response(
                {'error': _('حدث خطأ أثناء التسجيل. الرجاء المحاولة لاحقاً')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserLoginView(TokenObtainPairView):
    """تسجيل الدخول مع تحسينات"""
    serializer_class = UserLoginSerializer
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']

            refresh = RefreshToken.for_user(user)
            
            logger.info(f"User logged in: {user.phone}")

            return Response({
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': _('تم تسجيل الدخول بنجاح')
            })
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response(
                {'error': _('فشل تسجيل الدخول. الرجاء التحقق من البيانات')},
                status=status.HTTP_400_BAD_REQUEST
            )


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
            
            logger.info(f"User logged out: {request.user.phone}")
            
            return Response({
                'message': _('تم تسجيل الخروج بنجاح')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response(
                {'error': _('حدث خطأ أثناء تسجيل الخروج')},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """عرض وتحديث الملف الشخصي"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        logger.info(f"Profile updated for user: {request.user.phone}")
        
        return Response({
            'user': serializer.data,
            'message': _('تم تحديث الملف الشخصي بنجاح')
        })


class UserUpdateView(generics.UpdateAPIView):
    """تحديث بيانات المستخدم"""
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    """تغيير كلمة المرور مع تحسينات"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            
            logger.info(f"Password changed for user: {request.user.phone}")
            
            return Response({
                'message': _('تم تغيير كلمة المرور بنجاح')
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerificationRequestView(APIView):
    """تقديم طلب تحقق من الهوية"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        user = request.user
        
        # التحقق من توثيق رقم الهاتف أولاً
        if not user.phone_verified:
            return Response({
                'error': _('يجب توثيق رقم الهاتف أولاً')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # التحقق من عدم وجود طلب معلق
        if user.verification_status == 'pending':
            return Response({
                'error': _('لديك طلب تحقق معلق بالفعل')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # يمكن هنا إضافة منطق لرفع الوثائق
        user.verification_status = 'pending'
        user.save()
        
        logger.info(f"Verification requested for user: {user.phone}")
        
        return Response({
            'message': _('تم تقديم طلب التحقق بنجاح. سيقوم المسؤول بمراجعة طلبك.'),
            'verification_status': user.verification_status
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet للمستخدمين (للمشرفين)"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'user_type', 'verification_status', 'phone_verified']
    search_fields = ['phone', 'first_name', 'last_name', 'email']
    ordering_fields = ['date_joined', 'last_login', 'trust_score']
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['post'])
    def verify_user(self, request, pk=None):
        """توثيق هوية المستخدم (للمشرفين)"""
        user = self.get_object()
        user.verification_status = 'verified'
        user.trust_score = min(user.trust_score + 10, 100)  # زيادة درجة الثقة
        user.save()
        
        logger.info(f"User verified by admin: {user.phone} by {request.user.phone}")
        
        return Response({
            'message': _('تم توثيق المستخدم بنجاح'),
            'verification_status': user.verification_status
        })
    
    @action(detail=True, methods=['post'])
    def deactivate_user(self, request, pk=None):
        """تعطيل حساب المستخدم (للمشرفين)"""
        user = self.get_object()
        user.is_active = False
        user.save()
        
        logger.info(f"User deactivated by admin: {user.phone} by {request.user.phone}")
        
        return Response({
            'message': _('تم تعطيل الحساب بنجاح')
        })


class SendOTPView(APIView):
    """إرسال رمز التحقق (OTP) للهاتف"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [OTPRateThrottle]

    def post(self, request):
        user = request.user
        
        # التحقق من آخر طلب
        if user.last_otp_request:
            time_diff = timezone.now() - user.last_otp_request
            if time_diff < timedelta(minutes=2):
                remaining = 120 - int(time_diff.total_seconds())
                return Response({
                    'error': _('يجب الانتظار {} ثانية قبل طلب رمز جديد').format(remaining),
                    'remaining_seconds': remaining
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # إنشاء رمز عشوائي من 6 أرقام
        otp = str(random.randint(100000, 999999))
        
        # تخزين الرمز في الذاكرة المؤقتة
        cache.set(f'otp_{user.id}', otp, timeout=600)  # 10 دقائق
        
        # تحديث وقت آخر طلب
        user.last_otp_request = timezone.now()
        user.otp_attempts = 0
        user.save()
        
        # هنا يمكنك إرسال الـ OTP عبر SMS
        # TODO: استبدال هذا بخدمة SMS حقيقية في الإنتاج
        logger.info(f"OTP sent to {user.phone}: {otp}")
        
        # للتطوير فقط - في الإنتاج يجب إزالة هذا السطر
        if settings.DEBUG:
            return Response({
                'message': _('تم إرسال رمز التحقق إلى هاتفك بنجاح'),
                'debug_otp': otp  # فقط للتطوير!
            }, status=status.HTTP_200_OK)
        
        return Response({
            'message': _('تم إرسال رمز التحقق إلى هاتفك بنجاح')
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """التحقق من الرمز (OTP)"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        user = request.user
        otp_provided = request.data.get('otp')

        if not otp_provided:
            return Response({
                'error': _('يجب إدخال الرمز')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # التحقق من عدد المحاولات
        remaining_attempts = 5 - user.otp_attempts
        if user.otp_attempts >= 5:
            return Response({
                'error': _('لقد استنفدت جميع المحاولات. الرجاء طلب رمز جديد.'),
                'remaining_attempts': 0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # الحصول على الرمز من الذاكرة المؤقتة
        stored_otp = cache.get(f'otp_{user.id}')
        
        if stored_otp and stored_otp == otp_provided:
            # رمز صحيح
            user.phone_verified = True
            user.otp_attempts = 0
            user.trust_score = min(user.trust_score + 5, 100)  # زيادة درجة الثقة
            user.save()
            
            # حذف الرمز من الذاكرة
            cache.delete(f'otp_{user.id}')
            
            logger.info(f"Phone verified for user: {user.phone}")
            
            return Response({
                'message': _('تم توثيق رقم الهاتف بنجاح'),
                'phone_verified': True,
                'trust_score': user.trust_score
            }, status=status.HTTP_200_OK)
        
        # رمز خاطئ - زيادة عدد المحاولات
        user.otp_attempts += 1
        user.save()
        
        remaining_attempts = 5 - user.otp_attempts
        
        logger.warning(f"Failed OTP attempt for user {user.phone}. Attempts: {user.otp_attempts}")
        
        return Response({
            'error': _('رمز التحقق غير صحيح'),
            'remaining_attempts': remaining_attempts
        }, status=status.HTTP_400_BAD_REQUEST)