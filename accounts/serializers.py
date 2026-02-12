from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from .models import User, VolunteerProfile, AuditLog


class UserRegistrationSerializer(serializers.ModelSerializer):
    """سرياليزر تسجيل مستخدم جديد"""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'confirm_password', 
                 'phone', 'date_of_birth', 'gender', 'governorate', 'district', 'uzlah']
    
    def validate(self, data):
        """التحقق من تطابق كلمات المرور والتحقق من العمر"""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': _('كلمات المرور غير متطابقة')
            })
            
        
        # التحقق من العمر (يجب أن يكون 13+)
        if data.get('date_of_birth') :
            from datetime import date
            today = date.today()
            age = today.year - data['date_of_birth'].year - (
                (today.month, today.day) < (data['date_of_birth'].month, data['date_of_birth'].day)
            )
            if age < 13:
                raise serializers.ValidationError({
                    'date_of_birth': _('يجب أن يكون عمرك 13 سنة أو أكثر')
                })
        
        return data
    
    def create(self, validated_data):
        """إنشاء مستخدم جديد"""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # تسجيل في سجل التدقيق
        user.audit_logs.create(
            action_type='REGISTER',
            action_details=f'تسجيل مستخدم جديد: {user.email}'
        )
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """سرياليزر تسجيل الدخول"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        """التحقق من بيانات الدخول"""
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'), 
                               email=email, password=password)
            
            if not user:
                raise serializers.ValidationError(_('بيانات الدخول غير صحيحة'))
            
            if not user.is_active:
                raise serializers.ValidationError(_('الحساب معطل'))
                
            data['user'] = user
        else:
            raise serializers.ValidationError(_('يجب إدخال البريد الإلكتروني وكلمة المرور'))
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """سرياليزر عرض الملف الشخصي"""
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'national_id', 'date_of_birth', 
                 'age', 'gender', 'phone', 'governorate', 'district', 'uzlah',
                 'user_role', 'verification_status', 'is_blocked', 'blocking_reason',
                 'trust_score', 'total_reports', 'resolved_reports', 
                 'profile_picture', 'date_joined', 'last_login']
        read_only_fields = ['id', 'email', 'user_role', 'verification_status', 
                          'trust_score', 'date_joined', 'last_login']


class UserUpdateSerializer(serializers.ModelSerializer):
    """سرياليزر تحديث الملف الشخصي"""
    class Meta:
        model = User
        fields = ['full_name', 'phone', 'date_of_birth', 'gender', 'profile_picture']
    
    def update(self, instance, validated_data):
        """تحديث بيانات المستخدم"""
        user = super().update(instance, validated_data)
        
        # تسجيل في سجل التدقيق
        user.audit_logs.create(
            action_type='UPDATE_PROFILE',
            action_details='تحديث الملف الشخصي'
        )
        
        return user


class VolunteerProfileSerializer(serializers.ModelSerializer):
    """سرياليزر ملف المتطوع"""
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = VolunteerProfile
        fields = ['id', 'user', 'city', 'area', 'is_active_volunteer', 
                 'volunteer_since', 'total_contributions', 'skills', 
                 'languages', 'availability_hours']
        read_only_fields = ['id', 'user', 'volunteer_since', 'total_contributions']


class PasswordChangeSerializer(serializers.Serializer):
    """سرياليزر تغيير كلمة المرور"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, min_length=8, required=True)
    confirm_password = serializers.CharField(write_only=True, min_length=8, required=True)
    
    def validate(self, data):
        """التحقق من كلمة المرور القديمة وتطابق الجديدة"""
        user = self.context['request'].user
        
        # التحقق من كلمة المرور القديمة
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({
                'old_password': _('كلمة المرور القديمة غير صحيحة')
            })
        
        # التحقق من تطابق كلمات المرور الجديدة
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': _('كلمات المرور الجديدة غير متطابقة')
            })
        
        # التحقق من عدم استخدام كلمة المرور القديمة
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({
                'new_password': _('يجب أن تكون كلمة المرور الجديدة مختلفة عن القديمة')
            })
        
        return data
    
    def save(self):
        """حفظ كلمة المرور الجديدة"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        
        # تسجيل في سجل التدقيق
        user.audit_logs.create(
            action_type='CHANGE_PASSWORD',
            action_details='تغيير كلمة المرور'
        )
        
        return user


class AuditLogSerializer(serializers.ModelSerializer):
    """سرياليزر سجل التدقيق"""
    user_full_name = serializers.ReadOnlyField(source='user.full_name')
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_full_name', 'action_type', 'action_details', 
                 'ip_address', 'user_agent', 'created_at']


class UserAdminActionSerializer(serializers.Serializer):
    """سرياليزر إجراءات المشرف على المستخدمين"""
    action = serializers.ChoiceField(choices=['block', 'unblock', 'verify', 'reject_verification'])
    reason = serializers.CharField(required=False, allow_blank=True)