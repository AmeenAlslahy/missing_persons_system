from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """سرياليزر تسجيل مستخدم جديد"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['phone', 'first_name', 'middle_name', 'last_name', 'email',
                  'password', 'confirm_password',
                  'home_governorate', 'home_district', 'home_uzlah']
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': _('كلمات المرور غير متطابقة')
            })
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        # إنشاء المستخدم - create_user يقوم بتعيين كلمة المرور بشكل صحيح
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """سرياليزر تسجيل الدخول"""
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')
        
        if phone and password:
            user = authenticate(request=self.context.get('request'),
                                phone=phone, password=password)
            if not user:
                raise serializers.ValidationError(_('بيانات الدخول غير صحيحة'))
            if not user.is_active:
                raise serializers.ValidationError(_('الحساب معطل'))
            data['user'] = user
        else:
            raise serializers.ValidationError(_('يجب إدخال رقم الهاتف وكلمة المرور'))
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """سرياليزر عرض الملف الشخصي"""
    home_governorate_name = serializers.ReadOnlyField(source='home_governorate.name_ar')
    home_district_name = serializers.ReadOnlyField(source='home_district.name_ar')
    home_uzlah_name = serializers.ReadOnlyField(source='home_uzlah.name_ar')
    full_name = serializers.ReadOnlyField()
    user_type_display = serializers.SerializerMethodField()
    verification_status_display = serializers.SerializerMethodField()
    phone_verified_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name', 'first_name', 'middle_name', 'last_name', 'email',
                  'home_governorate', 'home_governorate_name', 'home_district', 'home_district_name', 
                  'home_uzlah', 'home_uzlah_name', 'user_type', 'user_type_display',
                  'verification_status', 'verification_status_display',
                  'phone_verified', 'phone_verified_display',
                  'trust_score', 'is_active', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login', 'trust_score']
    
    def get_user_type_display(self, obj):
        return obj.get_user_type_display()
    
    def get_verification_status_display(self, obj):
        return obj.get_verification_status_display()
    
    def get_phone_verified_display(self, obj):
        return "موثق" if obj.phone_verified else "غير موثق"

    def to_representation(self, instance):
        """إخفاء البيانات الحساسة لغير صاحب الحساب والمشرفين"""
        representation = super().to_representation(instance)
        request = self.context.get('request')
        user = request.user if request and request.user else None
        
        # إذا لم يكن المستخدم هو صاحب الحساب وليس مشرفاً
        if user and not user.is_staff and instance != user:
            # إخفاء الهاتف
            phone = representation.get('phone', '')
            if phone and len(phone) > 4:
                representation['phone'] = phone[:3] + '*' * (len(phone) - 5) + phone[-2:]
            
            # إخفاء البريد الإلكتروني
            email = representation.get('email', '')
            if email and '@' in email:
                parts = email.split('@')
                name = parts[0]
                domain = parts[1]
                if len(name) > 2:
                    representation['email'] = name[:2] + '*' * 5 + '@' + domain
                else:
                    representation['email'] = '*' * 5 + '@' + domain
        
        return representation


class UserUpdateSerializer(serializers.ModelSerializer):
    """سرياليزر تحديث الملف الشخصي"""
    class Meta:
        model = User
        fields = ['first_name', 'middle_name', 'last_name', 'email',
                  'home_governorate', 'home_district', 'home_uzlah']


class PasswordChangeSerializer(serializers.Serializer):
    """سرياليزر تغيير كلمة المرور"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, min_length=8, required=True)
    confirm_password = serializers.CharField(write_only=True, min_length=8, required=True)
    
    def validate(self, data):
        user = self.context['request'].user
        
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({
                'old_password': _('كلمة المرور القديمة غير صحيحة')
            })
        
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': _('كلمات المرور الجديدة غير متطابقة')
            })
        
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({
                'new_password': _('يجب أن تكون كلمة المرور الجديدة مختلفة عن القديمة')
            })
        
        return data
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user