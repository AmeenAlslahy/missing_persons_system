from rest_framework import generics, viewsets, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, SAFE_METHODS
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone

from .models import Report, ReportImage, Category, GeographicalArea, ReportAuditLog
from .serializers import (
    ReportSerializer, ReportUpdateSerializer, AdminReportSerializer,
    CategorySerializer, GeographicalAreaSerializer, ReportSearchSerializer,
    ReportImageSerializer, ReportReviewSerializer, ReportCloseSerializer
)
from accounts.permissions import IsVerifiedUser, IsVolunteerOrHigher
from matching.models import MatchResult


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet للبلاغات"""
    queryset = Report.objects.all().order_by('-created_at')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'status', 'city', 'gender', 'requires_admin_review']
    search_fields = ['person_name', 'report_code', 'contact_phone', 'last_seen_location']
    ordering_fields = ['created_at', 'last_seen_date', 'age']
    
    def get_serializer_class(self):
        """اختيار السرياليزر المناسب"""
        if self.request.user.is_staff:
            return AdminReportSerializer
        elif self.action in ['update', 'partial_update']:
            return ReportUpdateSerializer
        return ReportSerializer
    
    def get_permissions(self):
        """تحديد الصلاحيات"""
        if self.action in ['list', 'retrieve']:
            permission_classes = []  # Allow unauthenticated access for viewing
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

        # التحقق من حالة المصادقة
        if user.is_authenticated:
            # المشرف يرى كل البلاغات
            if user.is_staff:
                pass  # لا نحتاج لتصفية إضافية للمشرفين
            else:
                # المستخدم العادي يرى بلاغاته والبلاغات النشطة العامة
                queryset = queryset.filter(
                    Q(user=user) | Q(status='active')
                )
        else:
            # المستخدم غير المصادق يرى فقط البلاغات النشطة
            queryset = queryset.filter(status='active')

        # تصفية إضافية بناءً على معاملات البحث
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        gender = self.request.query_params.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)

        min_age = self.request.query_params.get('min_age')
        if min_age:
            queryset = queryset.filter(age__gte=min_age)

        max_age = self.request.query_params.get('max_age')
        if max_age:
            queryset = queryset.filter(age__lte=max_age)

        importance_level = self.request.query_params.get('importance_level')
        if importance_level:
            queryset = queryset.filter(importance_level=importance_level)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(person_name__icontains=search) |
                Q(report_code__icontains=search) |
                Q(contact_phone__icontains=search)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # بعد إنشاء البلاغ، نتحقق فوراً من وجود نتائج مطابقة تم إنشاؤها بواسطة الـ Signals
        report = serializer.instance
        matches = MatchResult.objects.filter(
            Q(missing_report=report) | Q(found_report=report)
        ).order_by('-similarity_score')
        
        headers = self.get_success_headers(serializer.data)
        data = serializer.data
        
        if matches.exists():
            best_match = matches.first()
            data['match_found'] = True
            data['match_count'] = matches.count()
            data['top_match_id'] = best_match.id
            data['top_match_similarity'] = best_match.similarity_score
            
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

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
                report.status = Report.Status.ACTIVE
                report.requires_admin_review = False
                message = _('تمت الموافقة على البلاغ')
            elif action == 'reject':
                report.status = Report.Status.REJECTED
                report.requires_admin_review = False
                report.rejection_reason = rejection_reason
                message = _('تم رفض البلاغ')

            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.review_notes = notes
            report.save()

            # تسجيل في سجل التدقيق
            try:
                ReportAuditLog.objects.create(
                    report=report,
                    user=request.user,
                    action_type=f'REVIEW_{action.upper()}',
                    action_details=f'مراجعة البلاغ: {notes}. السبب: {rejection_reason}',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except Exception as audit_error:
                # إذا فشل تسجيل السجل، لا نعطل العملية الأساسية
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to create audit log for report {report.pk}: {str(audit_error)}")

            return Response({
                'message': message,
                'report': AdminReportSerializer(report, context={'request': request}).data
            })
        except Exception as e:
            # تسجيل الخطأ في السجل
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in review action for report {pk}: {str(e)}")
            logger.error(f"Request data: {request.data}")
            logger.error(f"User: {request.user}")

            return Response(
                {'error': _('حدث خطأ أثناء تنفيذ الإجراء. يرجى المحاولة مرة أخرى.')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def resolve(self, request, pk=None):
        """حل البلاغ وإغلاقه مع ذكر السبب"""
        report = self.get_object()
        
        # فقط مالك البلاغ أو المشرف يمكنه حله
        if report.user != request.user and not request.user.is_staff:
            return Response(
                {'error': _('ليس لديك صلاحية حل هذا البلاغ')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReportCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        report.status = Report.Status.RESOLVED
        report.resolved_at = timezone.now()
        report.close_reason = serializer.validated_data['close_reason']
        report.save()
        
        # تحديث إحصائيات المستخدم إذا كان مالك البلاغ
        if report.user:
            report.user.resolved_reports += 1
            report.user.save()
        
        return Response({
            'message': _('تم حل البلاغ بنجاح'),
            'report': ReportSerializer(report).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def escalate(self, request, pk=None):
        """تصعيد البلاغ لأولوية قصوى"""
        report = self.get_object()
        report.importance_level = 'high'
        report.save()
        
        # تسجيل في سجل التدقيق
        ReportAuditLog.objects.create(
            report=report,
            user=request.user,
            action_type='ESCALATE',
            action_details='تصعيد البلاغ لأهمية عالية'
        )
        
        return Response({'message': 'تم تصعيد البلاغ بنجاح', 'importance_level': 'high'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def merge(self, request, pk=None):
        """دمج بلاغ مكرر في بلاغ آخر"""
        report = self.get_object()
        target_report_id = request.data.get('target_report_id')
        
        if not target_report_id:
            return Response({'error': 'يجب تحديد البلاغ الهدف للدمج'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            target_report = Report.objects.get(id=target_report_id)
        except Report.DoesNotExist:
            return Response({'error': 'البلاغ الهدف غير موجود'}, status=status.HTTP_404_NOT_FOUND)
            
        if target_report.id == report.id:
            return Response({'error': 'لا يمكن دمج البلاغ في نفسه'}, status=status.HTTP_400_BAD_REQUEST)
            
        report.merged_into = target_report
        report.status = Report.Status.CLOSED
        report.close_reason = f'دمج في البلاغ {target_report.report_code}'
        report.save()
        
        # تسجيل في سجل التدقيق
        ReportAuditLog.objects.create(
            report=report,
            user=request.user,
            action_type='MERGE',
            action_details=f'دمج البلاغ في {target_report.report_code}'
        )
        
        return Response({'message': f'تم دمج البلاغ بنجاح في {target_report.report_code}'})
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """بحث متقدم في البلاغات"""
        serializer = ReportSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        queryset = Report.objects.filter(status='active')
        
        # بناء استعلام البحث
        query_filters = Q()
        
        if data.get('query'):
            query_filters &= Q(
                Q(person_name__icontains=data['query']) |
                Q(last_seen_location__icontains=data['query']) |
                Q(distinctive_features__icontains=data['query'])
            )
        
        if data.get('report_type'):
            query_filters &= Q(report_type=data['report_type'])
        
        if data.get('city'):
            query_filters &= Q(city__icontains=data['city'])
        
        if data.get('gender'):
            query_filters &= Q(gender=data['gender'])
        
        if data.get('min_age'):
            query_filters &= Q(age__gte=data['min_age'])
        
        if data.get('max_age'):
            query_filters &= Q(age__lte=data['max_age'])
        
        if data.get('start_date'):
            query_filters &= Q(last_seen_date__gte=data['start_date'])
        
        if data.get('end_date'):
            query_filters &= Q(last_seen_date__lte=data['end_date'])
        
        queryset = queryset.filter(query_filters).order_by('-created_at')
        
        # التقسيم للصفحات
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReportSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReportSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet للفئات"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات الفئات"""
        stats = Category.objects.annotate(
            report_count=Count('reportcategory')
        ).order_by('-report_count')
        
        data = [{
            'id': cat.id,
            'name': cat.name,
            'report_count': cat.report_count,
            'priority_level': cat.priority_level
        } for cat in stats]
        
        return Response(data)


class GeographicalAreaViewSet(viewsets.ModelViewSet):
    """ViewSet للمناطق الجغرافية"""
    queryset = GeographicalArea.objects.all()
    serializer_class = GeographicalAreaSerializer
    permission_classes = [IsVolunteerOrHigher]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['city']
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """البحث عن مناطق قريبة"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', 10)  # كم
        
        if not lat or not lng:
            return Response(
                {'error': _('يجب إدخال خطوط الطول والعرض')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lat = float(lat)
            lng = float(lng)
            radius = float(radius)
        except ValueError:
            return Response(
                {'error': _('إحداثيات غير صالحة')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # هنا يمكن إضافة منطق حساب المسافات باستخدام Haversine formula
        # لكن مؤقتاً نرجع كل المناطق
        
        areas = GeographicalArea.objects.all()
        serializer = self.get_serializer(areas, many=True)
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
                'pending_review': Report.objects.filter(requires_admin_review=True).count(),
                'resolved_reports': Report.objects.filter(status='resolved').count(),
                'by_city': list(Report.objects.filter(city__isnull=False)
                               .values('city')
                               .annotate(count=Count('id'))
                               .order_by('-count')[:10]),
                'by_status': list(Report.objects.values('status')
                                 .annotate(count=Count('id')))
            }
        else:
            # إحصائيات للمستخدم العادي
            stats = {
                'my_reports': Report.objects.filter(user=user).count(),
                'my_active_reports': Report.objects.filter(user=user, status='active').count(),
                'my_resolved_reports': Report.objects.filter(user=user, status='resolved').count(),
                'total_active_reports': Report.objects.filter(status='active').count(),
            }
        
        return Response(stats)