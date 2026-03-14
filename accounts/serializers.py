from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
import re
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """سرياليزر تسجيل مستخدم جديد مع تحسينات"""
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        error_messages={
            'required': _('كلمة المرور مطلوبة'),
            'blank': _('كلمة المرور لا يمكن أن تكون فارغة')
        }
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'required': _('تأكيد كلمة المرور مطلوب'),
            'blank': _('تأكيد كلمة المرور لا يمكن أن يكون فارغاً')
        }
    )
    
    class Meta:
        model = User
        fields = [
            'phone', 'first_name', 'middle_name', 'last_name', 'email',
            'password', 'confirm_password',
            'home_governorate', 'home_district', 'home_uzlah'
        ]
    
    def validate_phone(self, value):
        """التحقق من صيغة رقم الهاتف"""
        # إزالة المسافات
        phone = value.strip()
        
        # التحقق من الصيغة
        pattern = r'^\+?[0-9]{8,15}$'
        if not re.match(pattern, phone):
            raise serializers.ValidationError(
                _('رقم الهاتف غير صحيح. يجب أن يتكون من 8 إلى 15 رقمًا، ويمكن أن يبدأ بـ +')
            )
        
        # التحقق من عدم وجود أرقام مكررة (اختياري)
        if len(set(phone.replace('+', ''))) < 3:
            raise serializers.ValidationError(
                _('رقم الهاتف ضعيف جداً. الرجاء استخدام رقم حقيقي')
            )
        
        return phone
    
    def validate_password(self, value):
        """التحقق من قوة كلمة المرور"""
        if len(value) < 8:
            raise serializers.ValidationError(
                _('كلمة المرور يجب أن تكون 8 أحرف على الأقل')
            )
        
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(
                _('كلمة المرور يجب أن تحتوي على رقم واحد على الأقل')
            )
        
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(
                _('كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل')
            )
        
        if not any(char.islower() for char in value):
            raise serializers.ValidationError(
                _('كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل')
            )
        
        # منع كلمات المرور الشائعة
        common_passwords = ['password123', '12345678', 'qwerty123']
        if value.lower() in common_passwords:
            raise serializers.ValidationError(
                _('كلمة المرور ضعيفة جداً. الرجاء اختيار كلمة مرور أقوى')
            )
        
        return value
    
    def validate(self, data):
        """التحقق من تطابق كلمات المرور"""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': _('كلمات المرور غير متطابقة')
            })
        
        # التحقق من وجود الاسم الأول واللقب
        if not data.get('first_name') or not data.get('last_name'):
            raise serializers.ValidationError(
                _('الاسم الأول واللقب مطلوبان')
            )
        
        return data
    
    def create(self, validated_data):
        """إنشاء مستخدم جديد"""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        # تنظيف البيانات
        if 'first_name' in validated_data:
            validated_data['first_name'] = validated_data['first_name'].strip()
        if 'last_name' in validated_data:
            validated_data['last_name'] = validated_data['last_name'].strip()
        
        # إنشاء المستخدم
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """سرياليزر تسجيل الدخول"""
    phone = serializers.CharField(
        error_messages={'required': _('رقم الهاتف مطلوب')}
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={'required': _('كلمة المرور مطلوبة')}
    )
    
    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')
        
        if phone and password:
            # تنظيف رقم الهاتف
            phone = phone.strip()
            
            user = authenticate(
                request=self.context.get('request'),
                phone=phone, 
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    _('رقم الهاتف أو كلمة المرور غير صحيحة')
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    _('هذا الحساب غير نشط. الرجاء التواصل مع الدعم')
                )
            
            # تحديث آخر نشاط
            user.update_last_activity()
            
            data['user'] = user
        else:
            raise serializers.ValidationError(
                _('يجب إدخال رقم الهاتف وكلمة المرور')
            )
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """سرياليزر عرض الملف الشخصي مع تحسينات"""
    home_governorate_name = serializers.ReadOnlyField(source='home_governorate.name_ar')
    home_district_name = serializers.ReadOnlyField(source='home_district.name_ar')
    home_uzlah_name = serializers.ReadOnlyField(source='home_uzlah.name_ar')
    full_name = serializers.ReadOnlyField()
    user_type_display = serializers.SerializerMethodField()
    verification_status_display = serializers.SerializerMethodField()
    phone_verified_display = serializers.SerializerMethodField()
    is_admin = serializers.BooleanField(read_only=True)
    account_age_days = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'full_name', 'first_name', 'middle_name', 'last_name', 'email',
            'home_governorate', 'home_governorate_name', 
            'home_district', 'home_district_name', 
            'home_uzlah', 'home_uzlah_name',
            'user_type', 'user_type_display',
            'verification_status', 'verification_status_display',
            'phone_verified', 'phone_verified_display',
            'trust_score', 'is_active', 'is_admin',
            'date_joined', 'last_login', 'last_activity', 'account_age_days'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 'last_activity', 
            'trust_score', 'phone_verified'
        ]
    
    def get_user_type_display(self, obj):
        return obj.get_user_type_display()
    
    def get_verification_status_display(self, obj):
        return obj.get_verification_status_display()
    
    def get_phone_verified_display(self, obj):
        return "موثق" if obj.phone_verified else "غير موثق"
    
    def get_account_age_days(self, obj):
        """حساب عمر الحساب بالأيام"""
        if obj.date_joined:
            days = (timezone.now() - obj.date_joined).days
            return days
        return 0

    def to_representation(self, instance):
        """إخفاء البيانات الحساسة لغير صاحب الحساب والمشرفين"""
        representation = super().to_representation(instance)
        request = self.context.get('request')
        
        if not request or not request.user:
            return representation
            
        user = request.user
        
        # إذا لم يكن المستخدم هو صاحب الحساب وليس مشرفاً
        if not user.is_admin() and instance != user:
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
            
            # إخفاء بعض الحقول الحساسة
            sensitive_fields = ['trust_score', 'last_login', 'last_activity']
            for field in sensitive_fields:
                if field in representation:
                    del representation[field]
        
        return representation


class UserUpdateSerializer(serializers.ModelSerializer):
    """سرياليزر تحديث الملف الشخصي"""
    
    class Meta:
        model = User
        fields = ['first_name', 'middle_name', 'last_name', 'email',
                  'home_governorate', 'home_district', 'home_uzlah']
    
    def validate_first_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError(
                _('الاسم الأول يجب أن يكون حرفين على الأقل')
            )
        return value.strip() if value else value
    
    def validate_last_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError(
                _('اللقب يجب أن يكون حرفين على الأقل')
            )
        return value.strip() if value else value
    
    def validate_email(self, value):
        if value:
            # التحقق من صيغة البريد الإلكتروني
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                raise serializers.ValidationError(
                    _('البريد الإلكتروني غير صحيح')
                )
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """سرياليزر تغيير كلمة المرور مع تحسينات"""
    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        error_messages={'required': _('كلمة المرور القديمة مطلوبة')}
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        error_messages={'required': _('كلمة المرور الجديدة مطلوبة')}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        error_messages={'required': _('تأكيد كلمة المرور مطلوب')}
    )
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_('كلمة المرور القديمة غير صحيحة'))
        return value
    
    def validate_new_password(self, value):
        """التحقق من قوة كلمة المرور الجديدة"""
        if len(value) < 8:
            raise serializers.ValidationError(
                _('كلمة المرور يجب أن تكون 8 أحرف على الأقل')
            )
        
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(
                _('كلمة المرور يجب أن تحتوي على رقم واحد على الأقل')
            )
        
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(
                _('كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل')
            )
        
        return value
    
    def validate(self, data):
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


class UserAdminSerializer(serializers.ModelSerializer):
    """سرياليزر للمشرفين - يعرض كل البيانات"""
    full_name = serializers.ReadOnlyField()
    reports_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = '__all__'
    
    def get_reports_count(self, obj):
        from reports.models import Report
        return Report.objects.filter(user=obj).count()