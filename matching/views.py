from datetime import timedelta
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
import logging

from .models import MatchResult, MatchingAuditLog, MatchFeedback
from .serializers import (
    MatchResultSerializer, MatchResultDetailSerializer,
    MatchReviewRequestSerializer, MatchRequestSerializer,
    MatchStatisticsSerializer, AdvancedMatchStatisticsSerializer,
    MatchFeedbackSerializer
)
from .matcher import ReportMatcher
from accounts.permissions import IsVolunteerOrHigher, IsAdminUser

logger = logging.getLogger(__name__)


class MatchResultViewSet(viewsets.ModelViewSet):
    """
    إدارة نتائج المطابقة
    """
    queryset = MatchResult.objects.all()
    permission_classes = [permissions.IsAuthenticated]
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
    ordering_fields = ['similarity_score', 'detected_at', 'updated_at', 'view_count']
    ordering = ['-similarity_score']
    
    def get_queryset(self):
        """تخصيص الاستعلام لجلب البيانات المرتبطة"""
        return MatchResult.objects.select_related(
            'report_1__person', 'report_2__person',
            'report_1__lost_governorate', 'report_2__lost_governorate',
            'report_1__lost_district', 'report_2__lost_district',
            'reviewed_by'
        ).prefetch_related(
            'report_1__images', 'report_2__images',
            'feedback'
        ).all()
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'review']:
            return MatchResultDetailSerializer
        return MatchResultSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def retrieve(self, request, *args, **kwargs):
        """زيادة عدد المشاهدات عند العرض"""
        instance = self.get_object()
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """مراجعة مطابقة مع خيارات متقدمة"""
        match_result = self.get_object()
        
        # التحقق من الصلاحيات
        is_owner = False
        if request.user.is_authenticated:
            if request.user == match_result.report_1.user or request.user == match_result.report_2.user:
                is_owner = True
                
        if not (request.user.is_staff or is_owner):
            return Response(
                {"error": "عذراً، لا تمتلك الصلاحية لتأكيد هذه المطابقة."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MatchReviewRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        decision = serializer.validated_data['decision']
        notes = serializer.validated_data['notes']
        
        # تحديث الحالة حسب القرار
        if decision == 'accept':
            match_result.match_status = 'accepted'
            message = 'تم قبول المطابقة وحل البلاغات المرتبطة'
            
            # تغيير حالة البلاغات إلى محلول
            match_result.report_1.status = 'resolved'
            match_result.report_2.status = 'resolved'
            match_result.report_1.save(update_fields=['status'])
            match_result.report_2.save(update_fields=['status'])
            
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
        
        # تسجيل في نظام التدقيق الشامل
        from audit.services import AuditService
        AuditService.log_action(
            user=request.user,
            action='REVIEW',
            resource_type='MatchResult',
            resource_id=str(match_result.match_id),
            data_after={'decision': decision, 'notes': notes},
            request=request
        )
        
        return Response({
            'status': 'reviewed',
            'match_status': match_result.match_status,
            'message': f'تم {message}'
        })
    
    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """إضافة تقييم للمطابقة"""
        match_result = self.get_object()
        
        # التحقق من عدم وجود تقييم سابق
        existing = MatchFeedback.objects.filter(
            match=match_result,
            user=request.user
        ).first()
        
        if existing:
            serializer = MatchFeedbackSerializer(existing, data=request.data, partial=True)
        else:
            serializer = MatchFeedbackSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(
                match=match_result,
                user=request.user
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
    
    @action(detail=False, methods=['get'])
    def my_matches(self, request):
        """المطابقات المرتبطة ببلاغات المستخدم"""
        user_reports = request.user.reports.values_list('report_id', flat=True)
        
        matches = self.get_queryset().filter(
            Q(report_1_id__in=user_reports) | Q(report_2_id__in=user_reports)
        )
        
        page = self.paginate_queryset(matches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(matches, many=True)
        return Response(serializer.data)


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
        
        # حساب نسبة النجاح
        total_reviewed = accepted_matches + rejected_matches + false_positive
        success_rate = (accepted_matches / total_reviewed * 100) if total_reviewed > 0 else 0
        
        # متوسط وقت المراجعة
        reviewed_matches = MatchResult.objects.filter(
            reviewed_at__isnull=False
        ).exclude(
            reviewed_at__isnull=True
        )
        
        if reviewed_matches.exists():
            total_time = sum(
                (m.reviewed_at - m.detected_at).total_seconds() / 3600
                for m in reviewed_matches
            )
            avg_response_time = total_time / reviewed_matches.count()
        else:
            avg_response_time = 0
        
        data = {
            'total_matches': total_matches,
            'pending_matches': pending_matches,
            'accepted_matches': accepted_matches,
            'rejected_matches': rejected_matches,
            'false_positive_matches': false_positive,
            'avg_similarity': round(avg_similarity, 2),
            'by_priority': {item['priority_level']: item['count'] for item in by_priority},
            'by_confidence': {item['confidence_level']: item['count'] for item in by_confidence},
            'success_rate': round(success_rate, 1),
            'avg_response_time': round(avg_response_time, 1)
        }
        
        serializer = MatchStatisticsSerializer(data=data)
        serializer.is_valid()
        return Response(serializer.data)


class AdvancedMatchStatisticsView(APIView):
    """إحصائيات متقدمة للمطابقات (للمشرفين فقط)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # إحصائيات شاملة
        stats = {
            'overall': {
                'total': MatchResult.objects.count(),
                'accepted': MatchResult.objects.filter(match_status='accepted').count(),
                'pending': MatchResult.objects.filter(match_status='pending').count(),
                'rejected': MatchResult.objects.filter(match_status='rejected').count(),
                'false_positive': MatchResult.objects.filter(match_status='false_positive').count(),
                'reviewing': MatchResult.objects.filter(match_status='reviewing').count(),
            },
            'time_based': {
                'today': MatchResult.objects.filter(detected_at__date=today).count(),
                'this_week': MatchResult.objects.filter(detected_at__date__gte=week_ago).count(),
                'this_month': MatchResult.objects.filter(detected_at__date__gte=month_ago).count(),
            },
            'performance': {
                'avg_processing_time': MatchingAuditLog.objects.filter(
                    action_type='batch_match',
                    status='success'
                ).aggregate(avg=Avg('processing_time'))['avg'] or 0,
                'success_rate': self._calculate_success_rate(),
                'total_processing_time': MatchingAuditLog.objects.aggregate(
                    total=Sum('processing_time')
                )['total'] or 0,
            },
            'by_type': {
                'auto': MatchResult.objects.filter(match_type='auto').count(),
                'manual': MatchResult.objects.filter(match_type='manual').count(),
            },
            'by_confidence': {
                level: MatchResult.objects.filter(confidence_level=level).count()
                for level, _ in MatchResult.CONFIDENCE_LEVELS
            },
            'by_priority': {
                level: MatchResult.objects.filter(priority_level=level).count()
                for level, _ in MatchResult.PRIORITY_LEVELS
            },
            'feedback_stats': self._get_feedback_stats(),
        }
        
        serializer = AdvancedMatchStatisticsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)
    
    def _calculate_success_rate(self):
        """حساب نسبة نجاح المطابقات التلقائية"""
        total = MatchResult.objects.filter(match_type='auto').count()
        if total == 0:
            return 0
        
        accepted = MatchResult.objects.filter(
            match_type='auto',
            match_status='accepted'
        ).count()
        
        return round((accepted / total) * 100, 2)
    
    def _get_feedback_stats(self):
        """إحصائيات تقييمات المستخدمين"""
        from django.db.models import Avg
        
        feedback = MatchFeedback.objects.all()
        
        return {
            'total': feedback.count(),
            'avg_rating': feedback.aggregate(avg=Avg('rating'))['avg'] or 0,
            'correct_count': feedback.filter(is_correct=True).count(),
        }