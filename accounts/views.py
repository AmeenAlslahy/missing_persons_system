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

from .models import User
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    UserProfileSerializer, UserUpdateSerializer,
    PasswordChangeSerializer
)

# Rate limiter مخصص لـ OTP
class OTPRateThrottle(UserRateThrottle):
    rate = '3/hour'  # 3 محاولات في الساعة


class UserRegistrationView(generics.CreateAPIView):
    """تسجيل مستخدم جديد"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]  # منع إنشاء حسابات كثيرة

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': _('تم إنشاء الحساب بنجاح')
        }, status=status.HTTP_201_CREATED)


class UserLoginView(TokenObtainPairView):
    """تسجيل الدخول"""
    serializer_class = UserLoginSerializer
    throttle_classes = [AnonRateThrottle]  # منع محاولات الدخول المتكررة

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
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
                # التحقق من أن token يخص المستخدم الحالي
                token = RefreshToken(refresh_token)
                if str(token.user_id) != str(request.user.id):
                    return Response({
                        'error': _('Token غير صالح لهذا المستخدم')
                    }, status=status.HTTP_400_BAD_REQUEST)
                token.blacklist()
            
            logout(request)
            return Response({
                'message': _('تم تسجيل الخروج بنجاح')
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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


class PasswordChangeView(APIView):
    """تغيير كلمة المرور"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': _('تم تغيير كلمة المرور بنجاح')
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerificationRequestView(APIView):
    """تقديم طلب تحقق من الهوية"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # التحقق من توثيق رقم الهاتف أولاً
        if not user.phone_verified:
            return Response({
                'error': _('يجب توثيق رقم الهاتف أولاً')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # يمكن هنا إضافة منطق لرفع الوثائق
        user.verification_status = 'pending'
        user.save()
        
        return Response({
            'message': _('تم تقديم طلب التحقق بنجاح. سيقوم المسؤول بمراجعة طلبك.'),
            'verification_status': user.verification_status
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet للمستخدمين (للمشرفين)"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'user_type', 'verification_status', 'home_governorate']
    search_fields = ['phone', 'first_name', 'last_name', 'email']
    ordering_fields = ['date_joined', 'last_login']
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class SendOTPView(APIView):
    """إرسال رمز التحقق (OTP) للهاتف"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [OTPRateThrottle]  # 3 محاولات كحد أقصى

    def post(self, request):
        user = request.user
        
        # التحقق من آخر طلب
        if user.last_otp_request and (timezone.now() - user.last_otp_request) < timedelta(minutes=2):
            return Response({
                'error': _('يجب الانتظار دقيقتين بين كل طلب وآخر')
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # إنشاء رمز عشوائي من 6 أرقام
        otp = str(random.randint(100000, 999999))
        
        # تخزين الرمز في الذاكرة المؤقتة (بدلاً من قاعدة البيانات)
        cache.set(f'otp_{user.id}', otp, timeout=600)  # 10 دقائق
        
        # تحديث وقت آخر طلب
        user.last_otp_request = timezone.now()
        user.otp_attempts = 0  # إعادة تعيين المحاولات
        user.save()
        
        # هنا يمكنك إرسال الـ OTP عبر SMS باستخدام خدمة خارجية
        # مثال: send_sms(user.phone, f"رمز التحقق الخاص بك هو: {otp}")
        
        # للتطوير فقط - في الإنتاج يجب إزالة هذا السطر
        print(f"OTP for {user.phone}: {otp}")  # TODO: Remove in production
        
        return Response({
            'message': _('تم إرسال رمز التحقق إلى هاتفك بنجاح')
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """التحقق من الرمز (OTP)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        otp_provided = request.data.get('otp')

        if not otp_provided:
            return Response({
                'error': _('يجب إدخال الرمز')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # التحقق من عدد المحاولات
        if user.otp_attempts >= 5:
            return Response({
                'error': _('لقد تجاوزت الحد الأقصى من المحاولات. الرجاء طلب رمز جديد.')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # الحصول على الرمز من الذاكرة المؤقتة
        stored_otp = cache.get(f'otp_{user.id}')
        
        if stored_otp and stored_otp == otp_provided:
            # رمز صحيح
            user.phone_verified = True
            user.otp_attempts = 0
            user.save()
            
            # حذف الرمز من الذاكرة
            cache.delete(f'otp_{user.id}')
            
            return Response({
                'message': _('تم توثيق رقم الهاتف بنجاح'),
                'phone_verified': True
            }, status=status.HTTP_200_OK)
        
        # رمز خاطئ - زيادة عدد المحاولات
        user.otp_attempts += 1
        user.save()
        
        remaining_attempts = 5 - user.otp_attempts
        return Response({
            'error': _('رمز التحقق غير صحيح'),
            'remaining_attempts': remaining_attempts
        }, status=status.HTTP_400_BAD_REQUEST)