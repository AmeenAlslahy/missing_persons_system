from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Governorate, District, Uzlah


class GovernorateSerializer(serializers.ModelSerializer):
    """سرياليزر المحافظة"""
    districts_count = serializers.IntegerField(read_only=True)
    uzlahs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Governorate
        fields = ['id', 'name', 'name_ar', 'name_en', 'code', 'population', 
                  'area', 'is_active', 'order', 'districts_count', 'uzlahs_count', 
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_uzlahs_count(self, obj):
        """عدد العزل في المحافظة"""
        return Uzlah.objects.filter(district__governorate=obj, is_active=True).count()
    
    def validate_code(self, value):
        """التحقق من كود المحافظة"""
        if value and len(value) < 2:
            raise serializers.ValidationError(_('كود المحافظة قصير جداً'))
        return value.upper() if value else value
    
    def validate(self, data):
        """التحقق من وجود اسم واحد على الأقل"""
        if not data.get('name') and not data.get('name_ar'):
            raise serializers.ValidationError(_('يجب إدخال الاسم أو الاسم بالعربية'))
        return data


class DistrictSerializer(serializers.ModelSerializer):
    """سرياليزر المديرية"""
    governorate_name = serializers.CharField(source='governorate.name', read_only=True)
    governorate_name_ar = serializers.CharField(source='governorate.name_ar', read_only=True)
    uzlahs_count = serializers.IntegerField(read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = District
        fields = ['id', 'governorate', 'governorate_name', 'governorate_name_ar', 
                  'full_name', 'name', 'name_ar', 'name_en', 'code', 
                  'population', 'is_active', 'order', 'uzlahs_count', 
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UzlahSerializer(serializers.ModelSerializer):
    """سرياليزر العزلة"""
    district_name = serializers.CharField(source='district.name', read_only=True)
    district_name_ar = serializers.CharField(source='district.name_ar', read_only=True)
    governorate_name = serializers.CharField(source='district.governorate.name', read_only=True)
    governorate_name_ar = serializers.CharField(source='district.governorate.name_ar', read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Uzlah
        fields = ['id', 'district', 'district_name', 'district_name_ar', 
                  'governorate_name', 'governorate_name_ar', 'full_name',
                  'name', 'name_ar', 'name_en', 'code', 'population', 
                  'is_active', 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DistrictDetailSerializer(DistrictSerializer):
    """سرياليزر تفصيلي للمديرية مع العزل"""
    uzlahs = UzlahSerializer(many=True, read_only=True)
    
    class Meta(DistrictSerializer.Meta):
        fields = DistrictSerializer.Meta.fields + ['uzlahs']


class GovernorateDetailSerializer(GovernorateSerializer):
    """سرياليزر تفصيلي للمحافظة مع المديريات"""
    districts = DistrictSerializer(many=True, read_only=True)
    
    class Meta(GovernorateSerializer.Meta):
        fields = GovernorateSerializer.Meta.fields + ['districts']