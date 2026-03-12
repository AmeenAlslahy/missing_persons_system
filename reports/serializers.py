from rest_framework import serializers
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date
from .models import Report, ReportImage, Person
from locations.models import Governorate, District, Uzlah



def get_client_ip(request):
    """دالة مساعدة للحصول على IP العميل"""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class ReportImageSerializer(serializers.ModelSerializer):
    """سرياليزر لصور البلاغات"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportImage
        fields = ['image_id', 'image_path', 'image_url', 'face_embedding', 
                 'quality_score', 'upload_at']
        read_only_fields = ['face_embedding', 'quality_score', 'upload_at']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image_path and request:
            try:
                return request.build_absolute_uri(obj.image_path.url)
            except Exception:
                return obj.image_path.url
        return None


class ReportSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    images = ReportImageSerializer(many=True, read_only=True)
    
    # حقول الشخص (للكتابة)
    person_first_name = serializers.CharField(write_only=True)
    person_middle_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    person_last_name = serializers.CharField(write_only=True)
    person_gender = serializers.ChoiceField(choices=Person.GENDER_CHOICES, write_only=True)
    person_date_of_birth = serializers.DateField(required=False, allow_null=True, write_only=True)
    approx_age = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # حقول إضافية للشخص
    person_blood_type = serializers.ChoiceField(choices=Person.BLOOD_TYPE_CHOICES, required=False, allow_blank=True, write_only=True)
    person_chronic_conditions = serializers.CharField(write_only=True, required=False, allow_blank=True)
    person_permanent_marks = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # موقع السكن (للكتابة)
    home_governorate = serializers.PrimaryKeyRelatedField(queryset=Governorate.objects.all(), required=False, allow_null=True, write_only=True)
    home_district = serializers.PrimaryKeyRelatedField(queryset=District.objects.all(), required=False, allow_null=True, write_only=True)
    home_uzlah = serializers.PrimaryKeyRelatedField(queryset=Uzlah.objects.all(), required=False, allow_null=True, write_only=True)

    # حقول العرض (للقراءة)
    person_id = serializers.ReadOnlyField(source='person.person_id')
    person_name = serializers.SerializerMethodField()
    person_gender_display = serializers.ReadOnlyField(source='person.get_gender_display')
    person_date_of_birth_display = serializers.DateField(source='person.date_of_birth', read_only=True)
    
    # موقع الفقدان (مجمع للواجهة)
    last_seen_location = serializers.SerializerMethodField()
    
    # معلومات العرض للسكن
    home_governorate_name = serializers.CharField(source='person.home_governorate.name_ar', read_only=True)
    home_district_name = serializers.CharField(source='person.home_district.name_ar', read_only=True)
    home_uzlah_name = serializers.CharField(source='person.home_uzlah.name_ar', read_only=True)
    
    # موقع الفقدان (من Report)
    lost_governorate_name = serializers.CharField(source='lost_governorate.name_ar', read_only=True)
    lost_district_name = serializers.CharField(source='lost_district.name_ar', read_only=True)
    lost_uzlah_name = serializers.CharField(source='lost_uzlah.name_ar', read_only=True)
    
    primary_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'report_id', 'report_code', 'user', 'report_type',
            'person_id', 'person_name', 'person_gender', 'person_gender_display',
            'person_first_name', 'person_middle_name', 'person_last_name',
            'person_date_of_birth', 'person_date_of_birth_display', 'approx_age',
            'person_blood_type', 'person_chronic_conditions', 'person_permanent_marks',
            'home_governorate', 'home_district', 'home_uzlah',
            'home_governorate_name', 'home_district_name', 'home_uzlah_name',
            'lost_governorate', 'lost_governorate_name',
            'lost_district', 'lost_district_name',
            'lost_uzlah', 'lost_uzlah_name', 'lost_location_details',
            'last_seen_date', 'last_seen_time', 'last_seen_location',
            'health_at_loss', 'medications', 'clothing_description', 'possessions',
            'status', 'importance', 'contact_phone', 'contact_person',
            'created_at', 'updated_at', 'resolved_at',
            'images', 'primary_photo'
        ]
        read_only_fields = ['report_id', 'report_code', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        # استخراج بيانات الشخص
        person_data = {
            'first_name': validated_data.pop('person_first_name'),
            'middle_name': validated_data.pop('person_middle_name', ''),
            'last_name': validated_data.pop('person_last_name'),
            'gender': validated_data.pop('person_gender'),
            'date_of_birth': validated_data.pop('person_date_of_birth', None),
            'blood_type': validated_data.pop('person_blood_type', ''),
            'chronic_conditions': validated_data.pop('person_chronic_conditions', ''),
            'permanent_marks': validated_data.pop('person_permanent_marks', ''),
            'home_governorate': validated_data.pop('home_governorate', None),
            'home_district': validated_data.pop('home_district', None),
            'home_uzlah': validated_data.pop('home_uzlah', None),
        }
        
        # معالجة العمر التقريبي إذا وجد
        approx_age = validated_data.pop('approx_age', None)
        if not person_data['date_of_birth'] and approx_age:
            today = timezone.now().date()
            person_data['date_of_birth'] = date(today.year - approx_age, 1, 1)

        # إنشاء الشخص
        person = Person.objects.create(**person_data)
        
        # إنشاء البلاغ
        validated_data['person'] = person
        report = Report.objects.create(**validated_data)
        
        # معالجة الصور المرفوعة
        request = self.context.get('request')
        if request and request.FILES:
            images = request.FILES.getlist('images')
            for image in images:
                ReportImage.objects.create(report=report, image_path=image)
        
        return report

    def get_person_name(self, obj):
        return obj.person.full_name if obj.person else ""

    def get_primary_photo(self, obj):
        first_image = obj.images.first()
        if first_image and first_image.image_path:
            request = self.context.get('request')
            if request:
                try:
                    return request.build_absolute_uri(first_image.image_path.url)
                except Exception:
                    return first_image.image_path.url
            return first_image.image_path.url
        return None

    def get_last_seen_location(self, obj):
        parts = []
        if obj.lost_governorate and obj.lost_governorate.name_ar:
            parts.append(obj.lost_governorate.name_ar)
        if obj.lost_district and obj.lost_district.name_ar:
            parts.append(obj.lost_district.name_ar)
        if obj.lost_uzlah and obj.lost_uzlah.name_ar:
            parts.append(obj.lost_uzlah.name_ar)
        return " - ".join(parts) if parts else _("غير محدد")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        user = request.user if request and request.user else None
        
        if user and not user.is_staff and instance.user != user:
            phone = representation.get('contact_phone', '')
            if phone and len(phone) > 4:
                representation['contact_phone'] = phone[:3] + '*' * (len(phone) - 5) + phone[-2:]
        
        return representation


class ReportReviewSerializer(serializers.Serializer):
    """سرياليزر مراجعة المشرف للبلاغات"""
    action = serializers.ChoiceField(choices=['accept', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        action = data.get('action')
        rejection_reason = data.get('rejection_reason')

        if action == 'reject' and not rejection_reason:
            raise serializers.ValidationError({
                'rejection_reason': _('يجب تحديد سبب الرفض عند رفض البلاغ')
            })

        return data


class ReportCloseSerializer(serializers.Serializer):
    """سرياليزر إغلاق البلاغ"""
    close_reason = serializers.CharField(required=True)


class ReportStatisticsSerializer(serializers.Serializer):
    """سرياليزر إحصائيات البلاغات"""
    total_reports = serializers.IntegerField(required=False, default=0)
    missing_reports = serializers.IntegerField(required=False, default=0)
    found_reports = serializers.IntegerField(required=False, default=0)
    active_reports = serializers.IntegerField(required=False, default=0)
    pending_review = serializers.IntegerField(required=False, default=0)
    resolved_reports = serializers.IntegerField(required=False, default=0)
    my_reports = serializers.IntegerField(required=False, default=0)
    my_active_reports = serializers.IntegerField(required=False, default=0)
    my_resolved_reports = serializers.IntegerField(required=False, default=0)
    total_active_reports = serializers.IntegerField(required=False, default=0)
    status_breakdown = serializers.DictField(required=False, default=dict)
    
    # ✅ تغيير from by_city to by_governorate
    by_governorate = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    by_status = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    
    # ✅ إضافة حقول جديدة
    by_gender = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    avg_age_at_loss = serializers.FloatField(required=False, default=0)


# السطر 176-200 - استبدل حقل city
class ReportSearchSerializer(serializers.Serializer):
    """سرياليزر للبحث في البلاغات"""
    query = serializers.CharField(required=False, allow_blank=True)
    report_type = serializers.CharField(required=False, allow_blank=True)
    
    # ✅ التوافق مع الإصدارات السابقة
    governorate = serializers.CharField(required=False, allow_blank=True)
    governorate_id = serializers.IntegerField(required=False, allow_null=True)
    
    gender = serializers.CharField(required=False, allow_blank=True)
    min_age = serializers.IntegerField(required=False, min_value=0)
    max_age = serializers.IntegerField(required=False, min_value=0)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    
    def validate(self, data):
        if data.get('min_age') and data.get('max_age'):
            if data['min_age'] > data['max_age']:
                raise serializers.ValidationError({
                    'min_age': _('الحد الأدنى للعمر يجب أن يكون أقل من الحد الأقصى')
                })
        
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError({
                    'start_date': _('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
                })
        
        return data