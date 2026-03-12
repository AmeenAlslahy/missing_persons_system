from rest_framework import serializers
from .models import Governorate, District, Uzlah


class GovernorateSerializer(serializers.ModelSerializer):
    """سرياليزر المحافظة"""
    districts_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Governorate
        fields = ['id', 'name', 'name_ar', 'name_en', 'code', 'population', 
                  'area', 'is_active', 'order', 'districts_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class DistrictSerializer(serializers.ModelSerializer):
    """سرياليزر المديرية"""
    governorate_name = serializers.CharField(source='governorate.name', read_only=True)
    uzlahs_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = District
        fields = ['id', 'governorate', 'governorate_name', 'name', 'name_ar', 
                  'name_en', 'code', 'population', 'is_active', 'order', 
                  'uzlahs_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class UzlahSerializer(serializers.ModelSerializer):
    """سرياليزر العزلة"""
    district_name = serializers.CharField(source='district.name', read_only=True)
    governorate_name = serializers.CharField(source='district.governorate.name', read_only=True)
    
    class Meta:
        model = Uzlah
        fields = ['id', 'district', 'district_name', 'governorate_name', 'name', 
                  'name_ar', 'name_en', 'code', 'population', 'is_active', 
                  'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class DistrictDetailSerializer(DistrictSerializer):
    """سرياليزر تفصيلي للمديرية مع العزل"""
    uzlahs = UzlahSerializer(many=True, read_only=True, source='uzlahs.filter(is_active=True)')
    
    class Meta(DistrictSerializer.Meta):
        fields = DistrictSerializer.Meta.fields + ['uzlahs']


class GovernorateDetailSerializer(GovernorateSerializer):
    """سرياليزر تفصيلي للمحافظة مع المديريات"""
    districts = DistrictSerializer(many=True, read_only=True, source='districts.filter(is_active=True)')
    
    class Meta(GovernorateSerializer.Meta):
        fields = GovernorateSerializer.Meta.fields + ['districts']