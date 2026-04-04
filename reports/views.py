from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Case, When, IntegerField, F
from django.db.models.functions import ExtractYear
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date
import logging
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Report, Person
from .serializers import (
    ReportPublicSerializer, ReportAdminSerializer, ReportCreateSerializer,
    ReportReviewSerializer, ReportCloseSerializer, ReportStatisticsSerializer,
    ReportSearchSerializer, PersonSearchSerializer, 
    ReportFromExistingPersonSerializer
)
from .utils import apply_age_filter, obfuscate_phone
from audit.services import AuditService
from utils.serializers import ErrorResponseSerializer

logger = logging.getLogger(__name__)


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet للبلاغات"""
    queryset = Report.objects.select_related(
        'person', 'user', 
        'lost_governorate', 'lost_district'
    ).prefetch_related(
        'images'
    ).all()
    
    @swagger_auto_schema(
        responses={
            401: 'Unauthorized',
            403: 'Forbidden',
            404: openapi.Response(
                'البلاغ غير موجود',
                examples={
                    'application/json': {
                        'success': False,
                        'error_code': 'NOTFOUND_003',
                        'message': 'البلاغ غير موجود',
                        'message_en': 'Report not found',
                        'details': None,
                        'timestamp': '2026-04-04T12:00:00Z'
                    }
                }
            ),
            500: 'Internal Server Error'
        }
    )
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'status', 'lost_governorate', 'importance']
    search_fields = ['person__first_name', 'person__last_name', 'report_code']
    ordering_fields = ['created_at', 'last_seen_date']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """اختيار السرياليزر المناسب حسب الصلاحية"""
        if self.action == 'create':
            return ReportCreateSerializer
        
        if self.request.user and self.request.user.is_staff:
            return ReportAdminSerializer
        
        return ReportPublicSerializer
    
    def get_permissions(self):
        """تحديد الصلاحيات لكل action"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        elif self.action in ['review', 'escalate']:
            permission_classes = [IsAdminUser]
        elif self.action == 'resolve':
            permission_classes = [IsAuthenticated]
        elif self.action == 'matches':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """تصفية البلاغات بناءً على صلاحيات المستخدم"""
        queryset = super().get_queryset()
        user = self.request.user

        # تصفية حسب الصلاحيات
        if user and user.is_authenticated:
            if user.is_staff:
                # المشرف يرى كل البلاغات
                pass
            else:
                # المستخدم العادي يرى بلاغاته والبلاغات النشطة والمحلولة فقط
                queryset = queryset.filter(
                    Q(user=user) | Q(status__in=['active', 'resolved'])
                )
        else:
            # المستخدم غير المصادق يرى فقط البلاغات النشطة والمحلولة
            queryset = queryset.filter(status__in=['active', 'resolved'])

        # الافتراضي للمستخدم العادي هو البلاغات النشطة إلا إذا طلب المحلولة
        if not user.is_staff:
            status_param = self.request.query_params.get('status')
            if not status_param:
                queryset = queryset.filter(status='active')

        # تطبيق الفلاتر من query params
        report_type = self.request.query_params.get('report_type')
        if report_type and report_type in dict(Report.REPORT_TYPES):
            queryset = queryset.filter(report_type=report_type)

        gender = self.request.query_params.get('gender')
        if gender and gender in dict(Person.GENDER_CHOICES):
            queryset = queryset.filter(person__gender=gender)

        # تطبيق فلتر العمر باستخدام الدالة المساعدة
        min_age = self.request.query_params.get('min_age')
        max_age = self.request.query_params.get('max_age')
        queryset = apply_age_filter(queryset, min_age, max_age)

        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter in dict(Report.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter)

        governorate = self.request.query_params.get('governorate')
        if governorate and governorate.isdigit():
            queryset = queryset.filter(lost_governorate_id=int(governorate))

        district = self.request.query_params.get('district')
        if district and district.isdigit():
            queryset = queryset.filter(lost_district_id=int(district))

        return queryset

    @swagger_auto_schema(
        request_body=ReportCreateSerializer,
        responses={
            201: openapi.Response('تم إنشاء البلاغ بنجاح', ReportPublicSerializer),
            400: openapi.Response(
                'بلاغ مكرر أو بيانات غير صالحة',
                examples={
                    'application/json': {
                        'success': False,
                        'error_code': 'REPORT_001',
                        'message': 'يوجد بلاغ نشط لهذا الشخص بالفعل',
                        'message_en': 'Active report already exists for this person',
                        'details': {
                            'existing_report_id': '550e8400-e29b-41d4-a716-446655440000',
                            'existing_report_status': 'active'
                        },
                        'timestamp': '2026-04-04T12:00:00Z'
                    }
                }
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """إنشاء بلاغ جديد مع تحديث التطابقات المرتبطة"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # DRF pattern: call perform_create
        report = self.perform_create(serializer)
        
        # الحصول على معرف البلاغ المرتبط إن وجد
        related_report_id = request.data.get('related_match_id')
        
        # إذا اختار المستخدم ربط هذا البلاغ ببلاغ سابق
        if related_report_id:
            try:
                related_report = Report.objects.get(pk=related_report_id)
                
                # إجراء المطابقة بين البلاغين وتسجيل النتيجة عبر الخدمة المركزية
                from matching.services import link_and_match_two_reports
                
                if report.report_type == 'missing':
                    match, similarity = link_and_match_two_reports(report, related_report)
                else:
                    match, similarity = link_and_match_two_reports(related_report, report)
                    
                if match:
                    logger.info(f"Created pending match between {report.report_code} and {related_report.report_code} with score {similarity}.")
            except Exception as e:
                logger.error(f"Error relating report {related_report_id} to new report: {e}")
        
        # تسجيل العملية
        AuditService.log_action(
            user=request.user,
            action='CREATE',
            resource_type='Report',
            resource_id=str(report.report_id),
            data_after={'report_code': report.report_code},
            request=request
        )
        
        logger.info(f"New report created: {report.report_code} by user {request.user}")
        
        # إرجاع البيانات حسب صلاحية المستخدم
        if request.user.is_staff:
            response_serializer = ReportAdminSerializer(report, context={'request': request})
        else:
            response_serializer = ReportPublicSerializer(report, context={'request': request})
        
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """إنشاء بلاغ جديد مع إضافة المستخدم وتحديد الحالة"""
        request = self.request
        last_seen_date = serializer.validated_data.get('last_seen_date')
        user = request.user
        
        # تحديد حالة البلاغ
        report_status = 'pending'
        
        if user.is_staff:
            # المشرفين - البلاغ نشط مباشرة
            report_status = 'active'
        else:
            # المستخدم العادي
            today = date.today()
            if last_seen_date:
                # إذا كان تاريخ الفقدان/العثور هو نفس اليوم
                if last_seen_date == today:
                    report_status = 'active'
                # إذا كان أقدم بيوم أو أكثر -> يحتاج موافقة
                elif last_seen_date < today:
                    report_status = 'pending'
        
        # حفظ البلاغ
        report = serializer.save(user=user, status=report_status)
        
        # تشغيل المطابقة التلقائية (إذا كان البلاغ نشطاً)
        if report_status == 'active':
            self._run_matching(report)
            
        return report

    def _run_matching(self, report):
        """تشغيل المطابقة التلقائية في الخلفية"""
        try:
            from matching.services import run_matching_async
            run_matching_async(report.report_id, delay=3)
            logger.info(f"Delayed matching scheduled for report {report.report_code}")
        except Exception as e:
            logger.error(f"Error scheduling matching for report {report.report_code}: {e}", exc_info=True)
    
    @action(detail=True, methods=['post'])
    @swagger_auto_schema(
        request_body=ReportReviewSerializer,
        responses={
            200: openapi.Response('تمت مراجعة البلاغ بنجاح'),
            403: openapi.Response(
                'ممنوع - صلاحيات غير كافية',
                examples={
                    'application/json': {
                        'success': False,
                        'error_code': 'AUTH_002',
                        'message': 'يجب أن يكون المستخدم مسجلاً كمشرف',
                        'message_en': 'Insufficient permissions, admin access required',
                        'details': None,
                        'timestamp': '2026-04-04T12:00:00Z'
                    }
                }
            )
        }
    )
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
            
            # تسجيل العملية
            AuditService.log_action(
                user=request.user,
                action='REVIEW',
                resource_type='Report',
                resource_id=str(report.report_id),
                data_after={'status': report.status, 'notes': notes},
                request=request
            )
            
            logger.info(f"Report {report.report_code} reviewed by {request.user} with action {action}")

            return Response({
                'message': message,
                'status': report.status
            })
            
        except Exception as e:
            logger.error(f"Error in review action for report {pk}: {str(e)}")
            return Response(
                {'error': _('حدث خطأ أثناء مراجعة البلاغ')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """حل البلاغ وإغلاقه"""
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
        report.close_reason = serializer.validated_data.get('close_reason', '')
        report.save()
        
        # تسجيل العملية
        AuditService.log_action(
            user=request.user,
            action='RESOLVE',
            resource_type='Report',
            resource_id=str(report.report_id),
            data_after={'status': 'resolved'},
            request=request
        )
        
        logger.info(f"Report {report.report_code} resolved by {request.user}")
        
        return Response({
            'message': _('تم حل البلاغ بنجاح'),
            'status': report.status
        })

    @action(detail=True, methods=['get'])
    def matches(self, request, pk=None):
        """عرض المطابقات المرتبطة بهذا البلاغ"""
        try:
            from matching.models import MatchResult
            from matching.serializers import MatchResultSerializer
        except ImportError:
            return Response(
                {'error': _('خدمة المطابقة غير متوفرة')},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        report = self.get_object()
        
        matches = MatchResult.objects.filter(
            Q(report_1=report) | Q(report_2=report)
        ).select_related(
            'report_1__person', 'report_2__person'
        ).order_by('-similarity_score')
        
        # استخدام pagination
        page = self.paginate_queryset(matches)
        if page is not None:
            serializer = MatchResultSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = MatchResultSerializer(matches[:20], many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """تصعيد البلاغ لأولوية قصوى"""
        report = self.get_object()
        report.importance = 'high'
        report.save()
        
        AuditService.log_action(
            user=request.user,
            action='ESCALATE',
            resource_type='Report',
            resource_id=str(report.report_id),
            request=request
        )
        
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
        
        if data.get('query'):
            queryset = queryset.filter(
                Q(person__first_name__icontains=data['query']) |
                Q(person__last_name__icontains=data['query']) |
                Q(report_code__icontains=data['query'])
            )
        
        if data.get('report_type'):
            queryset = queryset.filter(report_type=data['report_type'])
        
        if data.get('governorate_id'):
            queryset = queryset.filter(lost_governorate_id=data['governorate_id'])
        
        if data.get('gender'):
            queryset = queryset.filter(person__gender=data['gender'])
        
        # استخدام الدالة المساعدة للعمر
        queryset = apply_age_filter(
            queryset, 
            data.get('min_age'), 
            data.get('max_age')
        )
        
        if data.get('start_date'):
            queryset = queryset.filter(last_seen_date__gte=data['start_date'])
        
        if data.get('end_date'):
            queryset = queryset.filter(last_seen_date__lte=data['end_date'])
        
        # ترتيب النتائج
        queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset[:100], many=True)
        return Response(serializer.data)


class ReportStatisticsView(APIView):
    """إحصائيات البلاغات - محسن باستخدام aggregate"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        stats = {}
        
        if user.is_staff:
            # استعلام واحد محسن للمشرفين
            from django.db.models import Count, Q, Avg, F, FloatField
            from django.db.models.functions import ExtractYear, Cast
            
            base_queryset = Report.objects
            
            # إحصائيات أساسية باستخدام aggregate
            basic_stats = base_queryset.aggregate(
                total_reports=Count('report_id'),
                missing_reports=Count('report_id', filter=Q(report_type='missing')),
                found_reports=Count('report_id', filter=Q(report_type='found')),
                active_reports=Count('report_id', filter=Q(status='active')),
                pending_review=Count('report_id', filter=Q(status='pending')),
                resolved_reports=Count('report_id', filter=Q(status='resolved')),
            )
            
            # إحصائيات حسب المحافظة
            by_governorate = list(
                base_queryset.values('lost_governorate__name_ar')
                .annotate(count=Count('report_id'))
                .filter(lost_governorate__name_ar__isnull=False)
                .order_by('-count')[:10]
            )
            
            # إحصائيات حسب الحالة
            by_status = list(
                base_queryset.values('status')
                .annotate(count=Count('report_id'))
                .order_by()
            )
            
            # إحصائيات حسب الجنس
            by_gender = list(
                base_queryset.values('person__gender')
                .annotate(count=Count('report_id'))
                .filter(person__gender__isnull=False)
                .order_by()
            )
            
            # متوسط العمر - حساب أكثر دقة
            avg_age_result = base_queryset.filter(
                person__date_of_birth__isnull=False,
                last_seen_date__isnull=False
            ).annotate(
                age_at_loss=ExtractYear('last_seen_date') - ExtractYear('person__date_of_birth')
            ).aggregate(
                avg_age=Avg('age_at_loss')
            )
            
            stats = {
                **basic_stats,
                'by_governorate': by_governorate,
                'by_status': by_status,
                'by_gender': by_gender,
                'avg_age_at_loss': avg_age_result['avg_age'] or 0,
            }
            
        else:
            # إحصائيات للمستخدم العادي
            user_reports = Report.objects.filter(user=user)
            
            stats = {
                'my_reports': user_reports.count(),
                'my_active_reports': user_reports.filter(status='active').count(),
                'my_resolved_reports': user_reports.filter(status='resolved').count(),
                'total_active_reports': Report.objects.filter(status='active').count(),
                'status_breakdown': {
                    'active': Report.objects.filter(status='active').count(),
                    'pending': user_reports.filter(status='pending').count(),
                    'resolved': user_reports.filter(status='resolved').count(),
                }
            }
        
        serializer = ReportStatisticsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)


class SearchPersonsView(APIView):
    """البحث عن أشخاص مشابهين بالاسم"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="البحث بالاسم", type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})
        
        # بحث بالاسم مع ترتيب حسب الصلة
        persons = Person.objects.filter(
            Q(first_name__icontains=query) |
            Q(middle_name__icontains=query) |
            Q(last_name__icontains=query)
        ).prefetch_related('reports', 'reports__images')[:20]
        
        serializer = PersonSearchSerializer(
            persons, 
            many=True, 
            context={'request': request}
        )
            
        return Response({'results': serializer.data})


class SearchPersonsWithReportsView(APIView):
    """
    البحث عن أشخاص مشابهين مع عرض البلاغات النشطة المرتبطة بهم
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="البحث بالاسم", type=openapi.TYPE_STRING)
        ]
    )
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})
        
        # البحث عن الأشخاص بالاسم
        persons = Person.objects.filter(
            Q(first_name__icontains=query) |
            Q(middle_name__icontains=query) |
            Q(last_name__icontains=query)
        ).prefetch_related('reports', 'reports__images')[:10]
        
        results = []
        for person in persons:
            # الحصول على البلاغات النشطة لهذا الشخص
            active_reports = person.reports.filter(status__in=['active', 'pending'])
            
            # الحصول على صورة الشخص من أحدث بلاغ
            all_reports = list(person.reports.all())
            latest_report = all_reports[0] if all_reports else None
            person_photo = self._get_primary_photo(latest_report, request) if latest_report else None
            
            results.append({
                'person_id': str(person.person_id),
                'full_name': person.full_name,
                'first_name': person.first_name,
                'middle_name': person.middle_name,
                'last_name': person.last_name,
                'gender': person.gender,
                'gender_display': person.get_gender_display(),
                'date_of_birth': person.date_of_birth,
                'age': person.age,
                'home_governorate': person.home_governorate_id,
                'home_governorate_name': person.home_governorate.name_ar if person.home_governorate else None,
                'home_district': person.home_district_id,
                'home_district_name': person.home_district.name_ar if person.home_district else None,
                'home_uzlah': person.home_uzlah_id,
                'home_uzlah_name': person.home_uzlah.name_ar if person.home_uzlah else None,
                'primary_photo': person_photo,
                'active_reports': [
                    {
                        'report_id': str(r.report_id),
                        'report_code': r.report_code,
                        'report_type': r.report_type,
                        'report_type_display': r.get_report_type_display(),
                        'status': r.status,
                        'last_seen_date': r.last_seen_date,
                        'lost_governorate_name': r.lost_governorate.name_ar if r.lost_governorate else None,
                        'primary_photo': self._get_primary_photo(r, request),
                    }
                    for r in active_reports
                ]
            })
        
        return Response({'results': results})
    
    def _get_primary_photo(self, report, request):
        first_image = report.images.first()
        if first_image and first_image.image_path:
            if request:
                try:
                    return request.build_absolute_uri(first_image.image_path.url)
                except Exception:
                    pass
            return getattr(first_image.image_path, 'url', None)
        return None

