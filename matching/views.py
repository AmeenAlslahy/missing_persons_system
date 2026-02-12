from django.shortcuts import render
from datetime import timedelta
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Avg, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import MatchResult, MatchingConfig, MatchingAuditLog, FaceEmbedding, MatchReview
from .serializers import (
    MatchResultSerializer, 
    MatchResultDetailSerializer,
    MatchReviewSerializer,
    MatchingConfigSerializer,
    MatchingAuditLogSerializer,
    FaceEmbeddingSerializer,
    MatchReviewRequestSerializer
)
from .matcher import FaceMatcher
from accounts.permissions import IsVolunteerOrHigher, IsAdminUser

class MatchResultViewSet(viewsets.ModelViewSet):
    """
    إدارة نتائج المطابقة
    """
    queryset = MatchResult.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsVolunteerOrHigher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        'match_status': ['exact'],
        'confidence_level': ['exact'],
        'match_type': ['exact'],
        'priority_level': ['exact'],
        'similarity_score': ['gte', 'lte'],
    }
    search_fields = [
        'missing_report__person_name', 
        'found_report__person_name',
        'missing_report__report_code',
        'found_report__report_code'
    ]
    ordering_fields = ['similarity_score', 'confidence_score', 'detected_at']
    ordering = ['-similarity_score']
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'review']:
            return MatchResultDetailSerializer
        return MatchResultSerializer
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """مراجعة مطابقة مع خيارات متقدمة"""
        match_result = self.get_object()
        serializer = MatchReviewRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            decision = serializer.validated_data['decision']
            notes = serializer.validated_data.get('notes', '')
            
            if not notes or len(notes) < 5:
                return Response({'error': 'يجب إضافة ملاحظات توضيحية (5 أحرف على الأقل) لاتخاذ هذا القرار'}, status=status.HTTP_400_BAD_REQUEST)
            
            if decision == 'accept':
                match_result.accept_match(request.user, notes)
            elif decision == 'reject':
                match_result.reject_match(request.user, notes)
            elif decision == 'false_positive':
                match_result.reject_match(request.user, notes, false_positive=True)
            elif decision == 'open_comm':
                match_result.communication_opened = True
                match_result.match_status = MatchResult.MatchStatus.REVIEWING
                match_result.save()
            
            # تسجيل المراجعة في جدول MatchReview
            MatchReview.objects.create(
                match=match_result,
                reviewer=request.user,
                decision=decision if decision in ['accept', 'reject'] else 'need_more_info',
                notes=notes
            )
            
            return Response({'status': 'reviewed', 'match_status': match_result.match_status, 'message': 'تم تحديث حالة المطابقة'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def find_matches(self, request):
        """تشغيل المطابقة يدوياً لبلاغ"""
        report_id = request.data.get('report_id')
        if not report_id:
            return Response({'error': 'report_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from reports.models import Report
            report = Report.objects.get(report_id=report_id)
            
            matcher = FaceMatcher()
            matches = matcher.find_matches_for_report(report)
            
            return Response({'matches_found': len(matches), 'matches': matches})
        except Report.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

class MatchingConfigViewSet(viewsets.ModelViewSet):
    """
    إدارة إعدادات المطابقة (للمشرفين فقط)
    """
    queryset = MatchingConfig.objects.all()
    serializer_class = MatchingConfigSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

class MatchStatisticsView(APIView):
    """
    إحصائيات المطابقة
    """
    permission_classes = [permissions.IsAuthenticated, IsVolunteerOrHigher]
    
    def get(self, request):
        total_matches = MatchResult.objects.count()
        accepted_matches = MatchResult.objects.filter(match_status='accepted').count()
        pending_matches = MatchResult.objects.filter(match_status='pending').count()
        avg_confidence = MatchResult.objects.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
        
        return Response({
            'total_matches': total_matches,
            'accepted_matches': accepted_matches,
            'pending_matches': pending_matches,
            'avg_confidence': round(avg_confidence, 2)
        })

class FaceEmbeddingViewSet(viewsets.ModelViewSet):
    """
    إدارة ومراقبة بصمات الوجوه ومعالجة الصور
    """
    queryset = FaceEmbedding.objects.all().order_by('-created_at')
    serializer_class = FaceEmbeddingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['processing_status', 'embedding_version']
    search_fields = ['image__report__person_name', 'image__report__report_code']
    ordering_fields = ['created_at', 'quality_score', 'confidence_score']
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """إعادة معالجة الصورة لاستخراج البصمة"""
        embedding = self.get_object()
        embedding.processing_status = 'pending'
        embedding.save()
        
        # TODO: Trigger background task for processing
        
        return Response({'status': 're-processing started', 'message': 'تمت إضافة الصورة لزمام المعالجة'})
