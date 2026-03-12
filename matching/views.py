from datetime import timedelta
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
import logging

from .models import MatchResult, MatchingAuditLog
from .serializers import (
    MatchResultSerializer, MatchResultDetailSerializer,
    MatchReviewRequestSerializer, MatchRequestSerializer,
    MatchStatisticsSerializer
)
from .matcher import ReportMatcher
from accounts.permissions import IsVolunteerOrHigher, IsAdminUser

logger = logging.getLogger(__name__)


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
        'report_1__person__first_name', 
        'report_1__person__last_name',
        'report_2__person__first_name',
        'report_2__person__last_name',
        'report_1__report_code',
        'report_2__report_code'
    ]
    ordering_fields = ['similarity_score', 'detected_at', 'updated_at']
    ordering = ['-similarity_score']
    
    def get_queryset(self):
        """تخصيص الاستعلام لجلب البيانات المرتبطة"""
        return MatchResult.objects.select_related(
            'report_1__person', 'report_2__person',
            'report_1__lost_governorate', 'report_2__lost_governorate',  # ✅ تعديل هنا
            'report_1__lost_district', 'report_2__lost_district'         # ✅ إضافة المديرية
        ).prefetch_related(
            'report_1__images', 'report_2__images'
        ).all()
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'review']:
            return MatchResultDetailSerializer
        return MatchResultSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """مراجعة مطابقة مع خيارات متقدمة"""
        match_result = self.get_object()
        serializer = MatchReviewRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        decision = serializer.validated_data['decision']
        notes = serializer.validated_data['notes']
        
        # تحديث الحالة حسب القرار
        if decision == 'accept':
            match_result.match_status = 'accepted'
            message = 'تم قبول المطابقة'
        elif decision == 'reject':
            match_result.match_status = 'rejected'
            message = 'تم رفض المطابقة'
        elif decision == 'false_positive':
            match_result.match_status = 'false_positive'
            message = 'تم تصنيفها كإيجابية خاطئة'
        elif decision == 'reviewing':
            match_result.match_status = 'reviewing'
            message = 'تم تحويلها للمراجعة اليدوية'
        
        match_result.reviewed_by = request.user
        match_result.reviewed_at = timezone.now()
        match_result.review_notes = notes
        match_result.save()
        
        # تسجيل في سجل التدقيق
        MatchingAuditLog.objects.create(
            action_type='review',
            status='success',
            message=f"تم {message} للمطابقة {match_result.match_id}",
            created_by=request.user
        )
        
        return Response({
            'status': 'reviewed',
            'match_status': match_result.match_status,
            'message': f'تم {message}'
        })
    
    @action(detail=False, methods=['post'])
    def find_matches(self, request):
        """تشغيل المطابقة يدوياً لبلاغ"""
        serializer = MatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        report_id = serializer.validated_data['report_id']
        
        try:
            from reports.models import Report
            report = Report.objects.get(report_id=report_id)
            
            matcher = ReportMatcher()
            matches_count = matcher.run_matching_for_report(report)
            
            return Response({
                'matches_found': matches_count,
                'message': f'تم العثور على {matches_count} مطابقة'
            })
            
        except Report.DoesNotExist:
            return Response(
                {'error': 'البلاغ غير موجود'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"خطأ في تشغيل المطابقة: {e}")
            return Response(
                {'error': 'حدث خطأ في تشغيل المطابقة'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """ملخص سريع للمطابقات"""
        total = self.get_queryset().count()
        pending = self.get_queryset().filter(match_status='pending').count()
        accepted = self.get_queryset().filter(match_status='accepted').count()
        
        return Response({
            'total': total,
            'pending': pending,
            'accepted': accepted,
            'pending_for_review': pending
        })


class MatchStatisticsView(APIView):
    """
    إحصائيات المطابقة
    """
    permission_classes = [permissions.IsAuthenticated, IsVolunteerOrHigher]
    
    def get(self, request):
        # إحصائيات أساسية
        total_matches = MatchResult.objects.count()
        pending_matches = MatchResult.objects.filter(match_status='pending').count()
        accepted_matches = MatchResult.objects.filter(match_status='accepted').count()
        rejected_matches = MatchResult.objects.filter(match_status='rejected').count()
        false_positive = MatchResult.objects.filter(match_status='false_positive').count()
        
        # متوسط التشابه
        avg_similarity = MatchResult.objects.aggregate(
            avg=Avg('similarity_score')
        )['avg'] or 0
        
        # حسب الأولوية
        by_priority = MatchResult.objects.values('priority_level').annotate(
            count=Count('match_id')
        )
        
        # حسب مستوى الثقة
        by_confidence = MatchResult.objects.values('confidence_level').annotate(
            count=Count('match_id')
        )
        
        data = {
            'total_matches': total_matches,
            'pending_matches': pending_matches,
            'accepted_matches': accepted_matches,
            'rejected_matches': rejected_matches,
            'false_positive_matches': false_positive,
            'avg_similarity': round(avg_similarity, 2),
            'by_priority': {item['priority_level']: item['count'] for item in by_priority},
            'by_confidence': {item['confidence_level']: item['count'] for item in by_confidence},
        }
        
        serializer = MatchStatisticsSerializer(data=data)
        serializer.is_valid()
        return Response(serializer.data)