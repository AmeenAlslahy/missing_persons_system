from rest_framework import generics, viewsets, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, fields
from django.db.models.functions import ExtractYear
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date, timedelta
import logging

from .models import Report, ReportImage
from .serializers import (
    ReportSerializer, ReportReviewSerializer, ReportCloseSerializer,
    ReportStatisticsSerializer, ReportSearchSerializer,
    ReportImageSerializer, get_client_ip
)
from accounts.permissions import IsVerifiedUser

logger = logging.getLogger(__name__)


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet للبلاغات"""
    queryset = Report.objects.select_related(
        'person', 'user', 
        'lost_governorate', 'lost_district', 'lost_uzlah'
    ).prefetch_related(
        'images'
    ).all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'status', 'lost_governorate', 'importance']
    search_fields = ['person__first_name', 'person__last_name', 'report_code', 'contact_phone']
    ordering_fields = ['created_at', 'last_seen_date']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """اختيار السرياليزر المناسب"""
        if self.request.user.is_staff:
            return ReportSerializer
        return ReportSerializer
    
    def get_permissions(self):
        """تحديد الصلاحيات"""
        if self.action in ['list', 'retrieve']:
            permission_classes = []  # يسمح للجميع بالمشاهدة
        elif self.action == 'create':
            permission_classes = [IsAuthenticated, IsVerifiedUser]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """تصفية البلاغات بناءً على صلاحيات المستخدم"""
        queryset = super().get_queryset()
        user = self.request.user

        # تصفية حسب الصلاحيات
        if user.is_authenticated:
            if user.is_staff:
                # المشرف يرى كل البلاغات
                pass
            else:
                # المستخدم العادي يرى بلاغاته والبلاغات النشطة
                queryset = queryset.filter(
                    Q(user=user) | Q(status='active')
                )
        else:
            # المستخدم غير المصادق يرى فقط البلاغات النشطة
            queryset = queryset.filter(status='active')

        # تطبيق الفلاتر من query params
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        gender = self.request.query_params.get('gender')
        if gender:
            queryset = queryset.filter(person__gender=gender)

        # ✅ تعديل فلتر العمر - استخدام date_of_birth
        min_age = self.request.query_params.get('min_age')
        if min_age:
            today = date.today()
            # حساب تاريخ الميلاد الذي يحقق العمر الأدنى
            # الشخص الذي عمره >= min_age يعني تاريخ ميلاده <= (today - min_age years)
            min_birth_date = date(today.year - int(min_age), today.month, today.day)
            queryset = queryset.filter(person__date_of_birth__lte=min_birth_date)

        max_age = self.request.query_params.get('max_age')
        if max_age:
            today = date.today()
            # الشخص الذي عمره <= max_age يعني تاريخ ميلاده >= (today - max_age years)
            max_birth_date = date(today.year - int(max_age), today.month, today.day)
            queryset = queryset.filter(person__date_of_birth__gte=max_birth_date)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # ✅ فلتر المحافظة
        governorate = self.request.query_params.get('governorate')
        if governorate:
            queryset = queryset.filter(lost_governorate_id=governorate)

        # ✅ فلتر المديرية
        district = self.request.query_params.get('district')
        if district:
            queryset = queryset.filter(lost_district_id=district)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(person__first_name__icontains=search) |
                Q(person__last_name__icontains=search) |
                Q(report_code__icontains=search) |
                Q(contact_phone__icontains=search)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        """إنشاء بلاغ جديد"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        report = serializer.instance
        logger.info(f"New report created: {report.report_code} by user {request.user}")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """إنشاء بلاغ جديد مع إضافة المستخدم"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def review(self, request, pk=None):
        """مراجعة البلاغ من قبل المشرف"""
        try:
            report = self.get_object()
            serializer = ReportReviewSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            rejection_reason = serializer.validated_data.get('rejection_reason', '')

            if action == 'accept':
                report.status = 'active'
                message = _('تمت الموافقة على البلاغ')
            elif action == 'reject':
                report.status = 'rejected'
                message = _('تم رفض البلاغ')

            report.save()
            
            logger.info(f"Report {report.report_code} reviewed by {request.user} with action {action}")

            return Response({
                'message': message,
                'report': ReportSerializer(report, context={'request': request}).data
            })
            
        except Exception as e:
            logger.error(f"Error in review action for report {pk}: {str(e)}")
            return Response(
                {'error': _('حدث خطأ أثناء تنفيذ الإجراء')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def resolve(self, request, pk=None):
        """حل البلاغ وإغلاقه مع ذكر السبب"""
        report = self.get_object()
        
        if report.user != request.user and not request.user.is_staff:
            return Response(
                {'error': _('ليس لديك صلاحية حل هذا البلاغ')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReportCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        report.status = 'resolved'
        report.resolved_at = timezone.now()
        report.save()
        
        logger.info(f"Report {report.report_code} resolved by {request.user}")
        
        return Response({
            'message': _('تم حل البلاغ بنجاح'),
            'report': ReportSerializer(report, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def escalate(self, request, pk=None):
        """تصعيد البلاغ لأولوية قصوى"""
        report = self.get_object()
        report.importance = 'high'
        report.save()
        
        logger.info(f"Report {report.report_code} escalated by {request.user}")
        
        return Response({
            'message': _('تم تصعيد البلاغ بنجاح'),
            'importance': 'high'
        })
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """بحث متقدم في البلاغات"""
        serializer = ReportSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        queryset = self.get_queryset()
        
        query_filters = Q()
        
        if data.get('query'):
            query_filters &= Q(
                Q(person__first_name__icontains=data['query']) |
                Q(person__last_name__icontains=data['query']) |
                Q(report_code__icontains=data['query'])
            )
        
        if data.get('report_type'):
            query_filters &= Q(report_type=data['report_type'])
        
        # ✅ تعديل فلتر المدينة - استخدام lost_governorate
        if data.get('governorate') or data.get('city'):
            city_value = data.get('governorate') or data.get('city')
            query_filters &= Q(lost_governorate__name_ar__icontains=city_value) | \
                             Q(lost_governorate__name_en__icontains=city_value)
        
        if data.get('governorate_id'):
            query_filters &= Q(lost_governorate_id=data['governorate_id'])
        
        if data.get('gender'):
            query_filters &= Q(person__gender=data['gender'])
        
        # ✅ تعديل فلتر العمر
        if data.get('min_age'):
            today = date.today()
            min_birth_date = date(today.year - int(data['min_age']), today.month, today.day)
            query_filters &= Q(person__date_of_birth__lte=min_birth_date)
        
        if data.get('max_age'):
            today = date.today()
            max_birth_date = date(today.year - int(data['max_age']), today.month, today.day)
            query_filters &= Q(person__date_of_birth__gte=max_birth_date)
        
        if data.get('start_date'):
            query_filters &= Q(last_seen_date__gte=data['start_date'])
        
        if data.get('end_date'):
            query_filters &= Q(last_seen_date__lte=data['end_date'])
        
        queryset = queryset.filter(query_filters)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReportSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ReportSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class ReportStatisticsView(APIView):
    """إحصائيات البلاغات"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        stats = {}
        
        if user.is_staff:
            # إحصائيات للمشرفين
            stats = {
                'total_reports': Report.objects.count(),
                'missing_reports': Report.objects.filter(report_type='missing').count(),
                'found_reports': Report.objects.filter(report_type='found').count(),
                'active_reports': Report.objects.filter(status='active').count(),
                'pending_review': Report.objects.filter(status='pending').count(),
                'resolved_reports': Report.objects.filter(status='resolved').count(),
                
                # ✅ تغيير from by_city to by_governorate
                'by_governorate': list(
                    Report.objects.values('lost_governorate__name_ar')
                    .annotate(count=Count('report_id'))
                    .order_by('-count')[:10]
                ),
                
                'status_breakdown': {
                    item['status']: item['count'] 
                    for item in Report.objects.values('status').annotate(count=Count('report_id')).order_by()
                },

                'by_status': list(
                    Report.objects.values('status')
                    .annotate(count=Count('report_id')).order_by()
                ),
                
                # ✅ إضافة إحصائيات جديدة
                'by_gender': list(
                    Report.objects.values('person__gender')
                    .annotate(count=Count('report_id')).order_by()
                ),
                
                'avg_age_at_loss': Report.objects.annotate(
                    calc_age=ExtractYear('last_seen_date') - ExtractYear('person__date_of_birth')
                ).aggregate(avg=Avg('calc_age'))['avg'] or 0,
            }
        else:
            # إحصائيات للمستخدم العادي
            stats = {
                'total_reports': Report.objects.filter(user=user).count(),
                'active_reports': Report.objects.filter(status='active').count(),
                'my_reports': Report.objects.filter(user=user).count(),
                'my_active_reports': Report.objects.filter(user=user, status='active').count(),
                'my_resolved_reports': Report.objects.filter(user=user, status='resolved').count(),
                'total_active_reports': Report.objects.filter(status='active').count(),
                'status_breakdown': {
                    'active': Report.objects.filter(status='active').count(),
                    'pending': Report.objects.filter(user=user, status='pending').count(),
                    'resolved': Report.objects.filter(user=user, status='resolved').count(),
                }
            }
        
        serializer = ReportStatisticsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)