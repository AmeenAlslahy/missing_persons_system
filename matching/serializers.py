from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from datetime import date
from reports.models import Report
from .models import MatchResult


class MatchResultSerializer(serializers.ModelSerializer):
    """سرياليزر لنتائج المطابقة"""
    missing_person_name = serializers.SerializerMethodField()
    found_person_name = serializers.SerializerMethodField()
    missing_report_code = serializers.CharField(source='report_1.report_code', read_only=True)
    found_report_code = serializers.CharField(source='report_2.report_code', read_only=True)
    missing_report_image = serializers.SerializerMethodField()
    found_report_image = serializers.SerializerMethodField()
    
    missing_report_age = serializers.SerializerMethodField()
    found_report_age = serializers.SerializerMethodField()
    missing_report_gender = serializers.SerializerMethodField()
    found_report_gender = serializers.SerializerMethodField()
    missing_report_city = serializers.SerializerMethodField()
    found_report_city = serializers.SerializerMethodField()
    
    confidence_level_display = serializers.CharField(source='get_confidence_level_display', read_only=True)
    match_type_display = serializers.CharField(source='get_match_type_display', read_only=True)
    match_status_display = serializers.CharField(source='get_match_status_display', read_only=True)
    priority_level_display = serializers.CharField(source='get_priority_level_display', read_only=True)
    
    class Meta:
        model = MatchResult
        fields = [
            'match_id', 'report_1', 'report_2', 
            'missing_person_name', 'found_person_name',
            'missing_report_code', 'found_report_code',
            'missing_report_age', 'found_report_age',
            'missing_report_gender', 'found_report_gender',
            'missing_report_city', 'found_report_city',
            'missing_report_image', 'found_report_image',
            'similarity_score', 'confidence_level', 'confidence_level_display',
            'match_type', 'match_type_display', 'match_status', 'match_status_display',
            'priority_level', 'priority_level_display', 'detected_at', 'updated_at'
        ]
        read_only_fields = ['match_id', 'detected_at', 'updated_at']
    
    def get_person_age(self, person):
        """حساب العمر من تاريخ الميلاد"""
        if person and person.date_of_birth:
            today = date.today()
            return today.year - person.date_of_birth.year
        return None
    
    def get_missing_person_name(self, obj):
        """الحصول على اسم الشخص المفقود"""
        missing = obj.missing_report
        return str(missing.person) if missing and missing.person else ""
    
    def get_found_person_name(self, obj):
        """الحصول على اسم الشخص المعثور عليه"""
        found = obj.found_report
        return str(found.person) if found and found.person else ""
    
    def get_missing_report_age(self, obj):
        """الحصول على عمر المفقود"""
        missing = obj.missing_report
        return self.get_person_age(missing.person) if missing and missing.person else None
    
    def get_found_report_age(self, obj):
        """الحصول على عمر المعثور عليه"""
        found = obj.found_report
        return self.get_person_age(found.person) if found and found.person else None
    
    def get_missing_report_gender(self, obj):
        """الحصول على جنس المفقود"""
        missing = obj.missing_report
        return missing.person.gender if missing and missing.person else None
    
    def get_found_report_gender(self, obj):
        """الحصول على جنس المعثور عليه"""
        found = obj.found_report
        return found.person.gender if found and found.person else None
    
    def get_missing_report_city(self, obj):
        """الحصول على مدينة المفقود (موقع الفقدان)"""
        missing = obj.missing_report
        if missing and hasattr(missing, 'lost_governorate') and missing.lost_governorate:
            return missing.lost_governorate.name_ar
        return None
    
    def get_found_report_city(self, obj):
        """الحصول على مدينة المعثور عليه (موقع العثور)"""
        found = obj.found_report
        if found and hasattr(found, 'lost_governorate') and found.lost_governorate:
            return found.lost_governorate.name_ar
        return None
    
    def get_missing_report_image(self, obj):
        """الحصول على صورة المفقود"""
        missing = obj.missing_report
        if missing:
            first_image = missing.images.first()
            if first_image and first_image.image_path:
                request = self.context.get('request')
                if request:
                    try:
                        return request.build_absolute_uri(first_image.image_path.url)
                    except:
                        return first_image.image_path.url
        return None
    
    def get_found_report_image(self, obj):
        """الحصول على صورة المعثور عليه"""
        found = obj.found_report
        if found:
            first_image = found.images.first()
            if first_image and first_image.image_path:
                request = self.context.get('request')
                if request:
                    try:
                        return request.build_absolute_uri(first_image.image_path.url)
                    except:
                        return first_image.image_path.url
        return None


class MatchResultDetailSerializer(MatchResultSerializer):
    """سرياليزر تفصيلي لنتائج المطابقة"""
    contact_info = serializers.SerializerMethodField()
    match_details = serializers.JSONField(read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    
    class Meta(MatchResultSerializer.Meta):
        fields = MatchResultSerializer.Meta.fields + [
            'match_reason', 'match_details', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'review_notes', 'contact_info'
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.full_name
        return None

    def get_contact_info(self, obj):
        """إظهار بيانات الاتصال فقط بعد قبول التطابق"""
        if obj.match_status == 'accepted':
            missing = obj.missing_report
            found = obj.found_report
            return {
                'missing_phone': missing.contact_phone if missing else None,
                'found_phone': found.contact_phone if found else None,
                'missing_person': missing.contact_person if missing else None,
                'found_person': found.contact_person if found else None,
            }
        return None


class MatchReviewRequestSerializer(serializers.Serializer):
    """سرياليزر لطلب مراجعة مطابقة"""
    DECISION_CHOICES = [
        ('accept', _('قبول')),
        ('reject', _('رفض')),
        ('false_positive', _('إيجابي خاطئ')),
        ('reviewing', _('مراجعة يدوية')),
    ]
    
    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    notes = serializers.CharField(required=True, min_length=5)
    
    def validate_notes(self, value):
        """التحقق من طول الملاحظات"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("يجب إضافة ملاحظات توضيحية (5 أحرف على الأقل)")
        return value.strip()


class MatchRequestSerializer(serializers.Serializer):
    """سرياليزر لطلب تشغيل مطابقة"""
    report_id = serializers.UUIDField(required=True)
    
    def validate_report_id(self, value):
        """التحقق من وجود البلاغ"""
        from reports.models import Report
        try:
            Report.objects.get(report_id=value)
        except Report.DoesNotExist:
            raise serializers.ValidationError("البلاغ غير موجود")
        return value


class MatchStatisticsSerializer(serializers.Serializer):
    """سرياليزر لإحصائيات المطابقة"""
    total_matches = serializers.IntegerField()
    pending_matches = serializers.IntegerField()
    accepted_matches = serializers.IntegerField()
    rejected_matches = serializers.IntegerField()
    false_positive_matches = serializers.IntegerField()
    avg_similarity = serializers.FloatField()
    by_priority = serializers.DictField()
    by_confidence = serializers.DictField()