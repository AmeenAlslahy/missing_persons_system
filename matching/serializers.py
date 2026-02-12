from rest_framework import serializers
from .models import MatchResult, MatchingConfig, MatchingAuditLog, MatchReview, FaceEmbedding

class MatchingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchingConfig
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'last_run_at']

class MatchingAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchingAuditLog
        fields = '__all__'

class MatchReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True)
    
    class Meta:
        model = MatchReview
        fields = ['id', 'reviewer', 'reviewer_name', 'decision', 'notes', 'evidence_links', 'reviewed_at']
        read_only_fields = ['reviewer', 'reviewed_at']

class MatchResultSerializer(serializers.ModelSerializer):
    missing_person_name = serializers.CharField(source='missing_report.person_name', read_only=True)
    found_person_name = serializers.CharField(source='found_report.person_name', read_only=True)
    missing_report_code = serializers.CharField(source='missing_report.report_code', read_only=True)
    found_report_code = serializers.CharField(source='found_report.report_code', read_only=True)
    missing_report_image = serializers.SerializerMethodField()
    found_report_image = serializers.SerializerMethodField()
    
    missing_report_age = serializers.IntegerField(source='missing_report.age', read_only=True)
    found_report_age = serializers.IntegerField(source='found_report.age', read_only=True)
    missing_report_gender = serializers.CharField(source='missing_report.gender', read_only=True)
    found_report_gender = serializers.CharField(source='found_report.gender', read_only=True)
    missing_report_city = serializers.CharField(source='missing_report.city', read_only=True)
    found_report_city = serializers.CharField(source='found_report.city', read_only=True)
    
    class Meta:
        model = MatchResult
        fields = [
            'id', 'match_id', 'missing_report', 'found_report', 
            'missing_person_name', 'found_person_name',
            'missing_report_code', 'found_report_code',
            'missing_report_age', 'found_report_age',
            'missing_report_gender', 'found_report_gender',
            'missing_report_city', 'found_report_city',
            'missing_report_image', 'found_report_image',
            'similarity_score', 'confidence_score', 'confidence_level',
            'match_type', 'match_status', 'priority_level', 'detected_at'
        ]
        read_only_fields = ['match_id', 'detected_at', 'confidence_level']
        
    def get_missing_report_image(self, obj):
        if obj.missing_report.primary_photo:
            return obj.missing_report.primary_photo.url
        return None
        
    def get_found_report_image(self, obj):
        if obj.found_report.primary_photo:
            return obj.found_report.primary_photo.url
        return None

class MatchResultDetailSerializer(MatchResultSerializer):
    reviews = MatchReviewSerializer(many=True, read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    
    contact_info = serializers.SerializerMethodField()
    
    class Meta(MatchResultSerializer.Meta):
        fields = MatchResultSerializer.Meta.fields + [
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_notes', 
            'match_details', 'matched_features', 
            'communication_opened', 'contact_info', 'reviews'
        ]

    def get_contact_info(self, obj):
        """إظهار بيانات الاتصال فقط بعد قبول التطابق"""
        if obj.match_status == 'accepted':
            return {
                'missing_phone': obj.missing_report.contact_phone,
                'missing_email': obj.missing_report.contact_email,
                'found_phone': obj.found_report.contact_phone,
                'found_email': obj.found_report.contact_email,
            }
        return None

class MatchRequestSerializer(serializers.Serializer):
    report_id = serializers.UUIDField()

class MatchReviewRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['accept', 'reject', 'false_positive', 'need_info', 'open_comm'])
    notes = serializers.CharField(required=False, allow_blank=True)
    false_positive = serializers.BooleanField(required=False, default=False)
    evidence_links = serializers.ListField(child=serializers.URLField(), required=False)

class FaceEmbeddingSerializer(serializers.ModelSerializer):
    report_name = serializers.CharField(source='image.report.person_name', read_only=True)
    report_code = serializers.CharField(source='image.report.report_code', read_only=True)
    image_url = serializers.CharField(source='image.image.url', read_only=True)
    
    class Meta:
        model = FaceEmbedding
        fields = [
            'id', 'image_url', 'report_name', 'report_code', 
            'embedding_version', 'face_count', 'face_analysis', 
            'quality_score', 'confidence_score', 'processing_status', 
            'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']