✅ المتطلبات المكتملة بالفعل
الرمز	المتطلب	الحالة	الموقع
SR-01	تسجيل دخول وتحقق هوية	✅ مكتمل	JWT + OTP في accounts
SR-02	التحقق من اكتمال وصحة البلاغ	✅ مكتمل	ReportCreateSerializer.validate()
SR-03	تحديد نوع البلاغ	✅ مكتمل	حقل report_type في Report
SR-04	صورة إجبارية للمعثور عليه	✅ مكتمل	تحقق في ReportCreateSerializer
SR-05	بيانات أساسية إجبارية للمفقود	✅ مكتمل	تحقق في ReportCreateSerializer
SR-06	صورة اختيارية للمفقودة أنثى	✅ مكتمل	تحقق حسب الجنس
SR-09	نشر تلقائي إذا كان تاريخ الفقدان = اليوم	✅ مكتمل	منطق في ReportCreateSerializer
SR-10	إحالة للمراجعة إذا كان تاريخ الفقدان سابق	✅ مكتمل	منطق في ReportCreateSerializer
SR-11	مراجعة المشرف (قبول/رفض)	✅ مكتمل	review action في ReportViewSet
SR-12	مطابقة بين مفقود ومعثور عليه فقط	✅ مكتمل	منطق في matching/matcher.py
SR-13	مطابقة تلقائية عند إدخال بلاغ	✅ مكتمل	run_matching_for_report في signals.py
SR-20	إدارة المستخدمين للمشرف	✅ مكتمل	UserViewSet ولوحة تحكم المشرف
SR-21	سجل تدقيق للعمليات الإدارية	✅ مكتمل	MatchingAuditLog في matching
SNFR-01	زمن استجابة < 3 ثواني	✅ مكتمل	تحسين أداء باستخدام select_related
SNFR-03	تشفير البيانات الحساسة	✅ مكتمل	HTTPS + JWT + إخفاء البيانات
SNFR-04	آليات تحكم في الصلاحيات	✅ مكتمل	permissions.py بأنواعها
SNFR-05	تقييد عرض البيانات الحساسة	✅ مكتمل	to_representation في serializers
🟡 المتطلبات المكتملة جزئياً (تحتاج تحسين)
الرمز	المتطلب	الفجوة	الإجراء المطلوب
SR-07	رفع الصور بالكاميرا أو المعرض	الباك إند يدعم رفع الصور لكن لا يفرق المصدر	لا تغيير - هذا من مسؤولية تطبيق الموبايل
SR-08	التحقق من أن الصورة تحتوي على وجه إنسان	❌ غير موجود	إضافة خدمة تحقق من الصور باستخدام AI
SR-14	مطابقة بالبيانات التعريفية	موجود لكن يمكن تحسينه	تحسين خوارزميات مطابقة النصوص
SR-15	مطابقة بالصور إذا توفرت	موجود	-
SR-16	مطابقة بالصور فقط (بدون بيانات)	موجود	-
SR-17	مطابقة بالبيانات فقط (بدون صور)	موجود	-
SR-18	إشعار الأطراف عند وجود تطابق	موجود لكن ليس لجميع الحالات	تحسين نظام الإشعارات
SR-19	مراجعة المشرف لنتائج المطابقة	موجود	-
SR-AI-01	نموذج ذكاء اصطناعي لمطابقة الوجوه	❌ غير موجود	يحتاج تطبيق
SR-AI-02	استخلاص خصائص رقمية من الوجوه	❌ غير موجود	يحتاج تطبيق
SR-AI-03	إنتاج نسبة تشابه رقمية	موجود	لكن يعتمد على embeddings حالياً
SR-AI-04	عتبة تشابه للتطابق	موجود (0.32)	-
SNFR-AI-01	دقة نموذج 90%+	❌ غير موجود	يحتاج تطبيق
SNFR-AI-02	نتائج متسقة وموثوقة	❌ غير موجود	يحتاج تطبيق
SNFR-AI-03	تحديث النموذج دون تأثير	❌ غير موجود	يحتاج تطبيق
❌ المتطلبات غير المكتملة (تحتاج تطوير)
المتطلب الرئيسي: البحث عن الأشخاص المشابهين عند إنشاء بلاغ
هذا المتطلب غير موجود في النظام الحالي ويحتاج إلى تطوير كامل.

المتطلب	الوصف	الأولوية
UR-??	عند إدخال اسم الشخص، يتم عرض أسماء مشابهة	🔴 عالية
UR-??	عرض بيانات الشخص كاملة مع الصورة	🔴 عالية
UR-??	تأكيد المستخدم أن هذا هو نفس الشخص	🔴 عالية
UR-??	فتح نموذج إنشاء بلاغ مع تعبئة البيانات الثابتة تلقائياً	🔴 عالية
UR-??	إجراء مطابقة تلقائية بعد إنشاء البلاغ	موجود
UR-??	عرض التطابقات الخاصة بالبلاغ في صفحة التفاصيل	موجود جزئياً
خطة تطوير المتطلبات الجديدة
المرحلة 1: البحث عن الأشخاص المشابهين
1. إضافة API جديد للبحث عن الأشخاص
python
# reports/views.py
class SearchPersonsView(APIView):
    """
    البحث عن أشخاص مشابهين بالاسم
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})
        
        # بحث ذكي مع ترتيب حسب درجة التشابه
        persons = Person.objects.filter(
            Q(first_name__icontains=query) |
            Q(middle_name__icontains=query) |
            Q(last_name__icontains=query)
        )[:20]
        
        # حساب درجة التشابه (يمكن استخدام Levenshtein distance)
        results = []
        for person in persons:
            similarity = self._calculate_name_similarity(query, person.full_name)
            if similarity > 0.3:  # عتبة التشابه
                results.append(self._serialize_person(person, similarity))
        
        # ترتيب حسب درجة التشابه
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return Response({'results': results[:10]})
    
    def _calculate_name_similarity(self, query, full_name):
        """حساب درجة التشابه بين النصوص"""
        # يمكن استخدام Levenshtein distance أو Jaccard similarity
        # للتبسيط، نستخدم containment حالياً
        query = query.lower()
        full_name = full_name.lower()
        if query in full_name:
            return 0.8
        return 0.0
    
    def _serialize_person(self, person, similarity):
        """تحويل بيانات الشخص إلى JSON"""
        last_report = person.reports.order_by('-created_at').first()
        primary_photo = self._get_person_photo(person)
        
        return {
            'person_id': person.person_id,
            'full_name': person.full_name,
            'first_name': person.first_name,
            'middle_name': person.middle_name,
            'last_name': person.last_name,
            'date_of_birth': person.date_of_birth,
            'gender': person.gender,
            'blood_type': person.blood_type,
            'chronic_conditions': person.chronic_conditions,
            'permanent_marks': person.permanent_marks,
            'height': person.height,
            'weight': person.weight,
            'body_build': person.body_build,
            'skin_color': person.skin_color,
            'hair_color': person.hair_color,
            'eye_color': person.eye_color,
            'description': person.description,
            'home_governorate': person.home_governorate_id,
            'home_governorate_name': person.home_governorate.name_ar if person.home_governorate else None,
            'home_district': person.home_district_id,
            'home_district_name': person.home_district.name_ar if person.home_district else None,
            'home_uzlah': person.home_uzlah_id,
            'home_uzlah_name': person.home_uzlah.name_ar if person.home_uzlah else None,
            'last_report': {
                'report_id': last_report.report_id if last_report else None,
                'report_code': last_report.report_code if last_report else None,
                'last_seen_date': last_report.last_seen_date if last_report else None,
                'lost_governorate_name': last_report.lost_governorate.name_ar if last_report and last_report.lost_governorate else None,
            } if last_report else None,
            'primary_photo': primary_photo,
            'similarity': similarity,
        }
    
    def _get_person_photo(self, person):
        """الحصول على أحدث صورة للشخص"""
        last_report = person.reports.prefetch_related('images').order_by('-created_at').first()
        if last_report:
            first_image = last_report.images.first()
            if first_image and first_image.image_path:
                request = self.request
                return request.build_absolute_uri(first_image.image_path.url)
        return None
2. إضافة Serializer لإنشاء بلاغ من شخص موجود
python
# reports/serializers.py
class ReportFromExistingPersonSerializer(serializers.ModelSerializer):
    """سرياليزر لإنشاء بلاغ من شخص موجود مسبقاً"""
    
    report_type = serializers.ChoiceField(choices=Report.REPORT_TYPES, required=True)
    last_seen_date = serializers.DateField(required=True)
    last_seen_time = serializers.TimeField(required=False, allow_null=True)
    
    lost_governorate = serializers.PrimaryKeyRelatedField(
        queryset=Governorate.objects.all(), required=True
    )
    lost_district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(), required=True
    )
    lost_uzlah = serializers.PrimaryKeyRelatedField(
        queryset=Uzlah.objects.all(), required=False, allow_null=True
    )
    lost_location_details = serializers.CharField(required=False, allow_blank=True)
    
    health_at_loss = serializers.CharField(required=True)
    medications = serializers.CharField(required=False, allow_blank=True)
    clothing_description = serializers.CharField(required=False, allow_blank=True)
    possessions = serializers.CharField(required=False, allow_blank=True)
    
    contact_phone = serializers.CharField(required=True)
    contact_person = serializers.CharField(required=False, allow_blank=True)
    
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5
    )
    
    class Meta:
        model = Report
        fields = [
            'report_type',
            'last_seen_date', 'last_seen_time',
            'lost_governorate', 'lost_district', 'lost_uzlah', 'lost_location_details',
            'health_at_loss', 'medications', 'clothing_description', 'possessions',
            'contact_phone', 'contact_person',
            'images'
        ]
    
    def create(self, validated_data):
        person_id = self.context['person_id']
        person = Person.objects.get(pk=person_id)
        
        images = validated_data.pop('images', [])
        
        validated_data['person'] = person
        validated_data['user'] = self.context['request'].user
        
        # إنشاء كود البلاغ
        import random
        import string
        report_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        validated_data['report_code'] = f"RP-{report_code}"
        
        report = Report.objects.create(**validated_data)
        
        for image in images:
            ReportImage.objects.create(report=report, image_path=image)
        
        return report
3. إضافة View لإنشاء بلاغ من شخص موجود
python
# reports/views.py
class CreateReportFromPersonView(APIView):
    """
    إنشاء بلاغ جديد لشخص موجود
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request, person_id):
        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return Response(
                {'error': 'الشخص غير موجود'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ReportFromExistingPersonSerializer(
            data=request.data,
            context={'request': request, 'person_id': person_id}
        )
        
        if serializer.is_valid():
            report = serializer.save()
            
            # تشغيل المطابقة التلقائية
            from matching.matcher import ReportMatcher
            matcher = ReportMatcher()
            matches_count = matcher.run_matching_for_report(report)
            
            # تسجيل العملية
            logger.info(f"Report created from existing person {person_id} by {request.user}")
            
            # تحديث الإحصائيات
            from analytics.services import AnalyticsService
            AnalyticsService().update_report_stats(report, created=True)
            
            response_data = ReportDetailSerializer(report, context={'request': request}).data
            response_data['matches_found'] = matches_count
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
4. إضافة المسارات الجديدة
python
# reports/urls.py
urlpatterns = [
    # ... المسارات الموجودة
    path('search-persons/', views.SearchPersonsView.as_view(), name='search-persons'),
    path('create-from-person/<uuid:person_id>/', views.CreateReportFromPersonView.as_view(), name='create-from-person'),
]
المرحلة 2: تحسين المطابقة الذكية
تحسين matching/matcher.py
python
# matching/matcher.py - إضافة دوال مطابقة متقدمة

def calculate_name_similarity_advanced(self, name1, name2):
    """
    حساب تشابه الأسماء باستخدام خوارزميات متقدمة
    """
    if not name1 or not name2:
        return 0.0
    
    import jellyfish  # مكتبة لحساب المسافات النصية
    
    # تطبيع الأسماء (إزالة التشكيل، توحيد الكتابة)
    name1 = self._normalize_arabic_text(name1)
    name2 = self._normalize_arabic_text(name2)
    
    # استخدام عدة خوارزميات للحصول على نتيجة أفضل
    levenshtein_sim = 1 - (jellyfish.levenshtein_distance(name1, name2) / max(len(name1), len(name2)))
    jaro_sim = jellyfish.jaro_winkler_similarity(name1, name2)
    
    # المتوسط المرجح
    return (levenshtein_sim * 0.4 + jaro_sim * 0.6)

def _normalize_arabic_text(self, text):
    """
    تطبيع النص العربي (إزالة التشكيل، توحيد الحروف)
    """
    # إزالة الحركات والتشكيل
    import re
    arabic_diacritics = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
    text = arabic_diacritics.sub('', text)
    
    # توحيد ألف (أ, إ, آ) إلى ا
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    
    # توحيد تاء مربوطة وهاء
    text = text.replace('ة', 'ه')
    
    return text.lower()
المرحلة 3: عرض التطابقات في صفحة التفاصيل
تعديل reports/views.py - إضافة action لعرض المطابقات
python
# reports/views.py - أضف داخل ReportViewSet

@action(detail=True, methods=['get'])
def matches(self, request, pk=None):
    """
    عرض جميع المطابقات المرتبطة بهذا البلاغ
    """
    report = self.get_object()
    
    # البحث عن المطابقات التي يشارك فيها هذا البلاغ
    from matching.models import MatchResult
    from matching.serializers import MatchResultSerializer
    
    matches = MatchResult.objects.filter(
        Q(report_1=report) | Q(report_2=report)
    ).select_related(
        'report_1__person', 'report_2__person',
        'report_1__lost_governorate', 'report_2__lost_governorate'
    ).order_by('-similarity_score')
    
    page = self.paginate_queryset(matches)
    if page is not None:
        serializer = MatchResultSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
    
    serializer = MatchResultSerializer(matches, many=True, context={'request': request})
    return Response(serializer.data)
المرحلة 4: تحسين نظام التدقيق والإحصائيات
إضافة AuditLog شامل
python
# create new app: auditlog
# auditlog/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class AuditLog(models.Model):
    ACTION_TYPES = [
        ('CREATE', 'إنشاء'),
        ('UPDATE', 'تحديث'),
        ('DELETE', 'حذف'),
        ('VIEW', 'مشاهدة'),
        ('LOGIN', 'تسجيل دخول'),
        ('LOGOUT', 'تسجيل خروج'),
        ('MATCH', 'مطابقة'),
        ('REVIEW', 'مراجعة'),
        ('VERIFY', 'تحقق'),
    ]
    
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True)
    user_phone = models.CharField(max_length=20, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    entity_type = models.CharField(max_length=50)  # Report, User, MatchResult, etc.
    entity_id = models.UUIDField(null=True, blank=True)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل التدقيق')
        verbose_name_plural = _('سجلات التدقيق')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action_type']),
            models.Index(fields=['timestamp']),
        ]
Middleware لتسجيل الطلبات
python
# auditlog/middleware.py

import threading
from django.utils import timezone

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # قبل المعالجة
        request.auditlog_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now(),
        }
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
المرحلة 5: تحسين الإحصائيات التلقائية
تعديل analytics/services.py
python
# analytics/services.py

def update_all_stats(self):
    """
    تحديث جميع الإحصائيات بشكل متكامل
    """
    today = timezone.now().date()
    
    # تحديث الإحصائيات اليومية
    daily_stats = self.update_daily_stats(today)
    
    # تحديث مقاييس الأداء
    self.update_performance_metrics()
    
    # تحديث التقارير المجدولة
    self._update_scheduled_reports()
    
    # تحديث إحصائيات المطابقة
    self._update_matching_stats()
    
    return daily_stats

def _update_matching_stats(self):
    """
    تحديث إحصائيات المطابقة
    """
    from matching.models import MatchResult
    from django.db.models import Count, Avg
    
    stats = {
        'total_matches': MatchResult.objects.count(),
        'accepted_matches': MatchResult.objects.filter(match_status='accepted').count(),
        'pending_matches': MatchResult.objects.filter(match_status='pending').count(),
        'rejected_matches': MatchResult.objects.filter(match_status='rejected').count(),
        'avg_similarity': MatchResult.objects.aggregate(Avg('similarity_score'))['similarity_score__avg'] or 0,
    }
    
    # تخزين في كاش للوصول السريع
    cache.set('matching_stats', stats, timeout=3600)
    
    return stats
مصفوفة الأولويات للتطوير
الأولوية	المتطلب	الوقت التقديري
🔴 عالية	البحث عن الأشخاص المشابهين	4 ساعات
🔴 عالية	إنشاء بلاغ من شخص موجود	3 ساعات
🟡 متوسطة	عرض المطابقات في صفحة التفاصيل	2 ساعة
🟡 متوسطة	تحسين خوارزميات المطابقة	5 ساعات
🟢 منخفضة	نظام تدقيق شامل	4 ساعات
🟢 منخفضة	إحصائيات متكاملة	3 ساعات
🔴 عالية	التحقق من الصور (وجه إنسان)	8 ساعات
🔴 عالية	نموذج ذكاء اصطناعي لمطابقة الوجوه	16 ساعة