from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from reports.models import Report
from matching.models import MatchResult
import uuid


class DailyStats(models.Model):
    """إحصائيات يومية"""
    date = models.DateField(_('التاريخ'), unique=True)
    
    # المستخدمون
    total_users = models.IntegerField(_('إجمالي المستخدمين'), default=0)
    new_users = models.IntegerField(_('مستخدمين جدد'), default=0)
    active_users = models.IntegerField(_('مستخدمين نشطين'), default=0)
    verified_users = models.IntegerField(_('مستخدمين موثوقين'), default=0)
    
    # البلاغات
    total_reports = models.IntegerField(_('إجمالي البلاغات'), default=0)
    new_reports = models.IntegerField(_('بلاغات جديدة'), default=0)
    missing_reports = models.IntegerField(_('بلاغات مفقودين'), default=0)
    found_reports = models.IntegerField(_('بلاغات معثور عليهم'), default=0)
    resolved_reports = models.IntegerField(_('بلاغات محلولة'), default=0)
    resolved_today = models.IntegerField(_('محلولة اليوم'), default=0)
    resolved_this_week = models.IntegerField(_('محلولة هذا الأسبوع'), default=0)
    resolved_this_month = models.IntegerField(_('محلولة هذا الشهر'), default=0)
    pending_review_reports = models.IntegerField(_('بلاغات قيد المراجعة'), default=0)
    
    # المطابقة
    total_matches = models.IntegerField(_('إجمالي المطابقات'), default=0)
    new_matches = models.IntegerField(_('مطابقات جديدة'), default=0)
    accepted_matches = models.IntegerField(_('مطابقات مقبولة'), default=0)
    false_positive_matches = models.IntegerField(_('مطابقات إيجابية خاطئة'), default=0)
    match_success_rate = models.FloatField(_('معدل نجاح المطابقة'), default=0.0)
    
    # النشاط
    total_logins = models.IntegerField(_('إجمالي عمليات الدخول'), default=0)
    total_searches = models.IntegerField(_('إجمالي عمليات البحث'), default=0)
    total_notifications = models.IntegerField(_('إجمالي الإشعارات'), default=0)
    
    # الأداء
    avg_response_time = models.FloatField(_('متوسط زمن الاستجابة'), default=0.0)
    avg_resolution_time = models.FloatField(_('متوسط زمن الحل (ساعات)'), default=0.0)
    system_uptime = models.FloatField(_('وقت تشغيل النظام'), default=100.0)
    error_rate = models.FloatField(_('معدل الأخطاء'), default=0.0)
    
    # الجغرافيا
    top_cities = models.JSONField(_('أهم المدن'), default=list)
    reports_by_gender = models.JSONField(_('البلاغات حسب الجنس'), default=dict)
    reports_by_age_group = models.JSONField(_('البلاغات حسب الفئة العمرية'), default=dict)
    
    # تحديث
    calculated_at = models.DateTimeField(_('تاريخ الحساب'), auto_now=True)
    
    class Meta:
        verbose_name = _('إحصائية يومية')
        verbose_name_plural = _('الإحصائيات اليومية')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"إحصائيات {self.date}"
    
    @classmethod
    def get_or_create_today(cls):
        """الحصول على إحصائيات اليوم أو إنشاؤها"""
        today = timezone.now().date()
        stats, created = cls.objects.get_or_create(date=today)
        
        if created:
            # حساب الإحصائيات الأولية
            stats.calculate_stats()
        
        return stats
    
    def calculate_stats(self):
        """حساب الإحصائيات"""
        from django.db.models import Count, Q, Avg
        from datetime import timedelta
        
        # المستخدمون
        stats_date = self.date
        start_date = stats_date
        end_date = stats_date + timedelta(days=1)
        
        # المستخدمون
        self.total_users = User.objects.count()
        self.new_users = User.objects.filter(
            date_joined__date=stats_date
        ).count()
        
        # المستخدمون النشطون (دخلوا خلال آخر 30 يوم)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        self.active_users = User.objects.filter(
            last_login__gte=thirty_days_ago
        ).count()
        
        self.verified_users = User.objects.filter(
            verification_status='verified'
        ).count()
        
        # البلاغات
        self.total_reports = Report.objects.count()
        self.new_reports = Report.objects.filter(
            created_at__date=stats_date
        ).count()
        
        self.missing_reports = Report.objects.filter(
            report_type='missing'
        ).count()
        
        self.found_reports = Report.objects.filter(
            report_type='found'
        ).count()
        
        self.resolved_reports = Report.objects.filter(
            status='resolved'
        ).count()
        
        # إحصائيات زمنية للحل
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        self.resolved_today = Report.objects.filter(
            status='resolved', updated_at__date=today
        ).count()
        self.resolved_this_week = Report.objects.filter(
            status='resolved', updated_at__date__gte=week_ago
        ).count()
        self.resolved_this_month = Report.objects.filter(
            status='resolved', updated_at__date__gte=month_ago
        ).count()
        
        # حساب متوسط زمن الحل
        resolved_with_time = Report.objects.filter(
            status='resolved', created_at__isnull=False, updated_at__isnull=False
        )
        if resolved_with_time.exists():
            total_time = sum(
                [(r.updated_at - r.created_at).total_seconds() for r in resolved_with_time],
                0
            )
            # النتيجة بالساعات
            self.avg_resolution_time = (total_time / resolved_with_time.count()) / 3600
        else:
            self.avg_resolution_time = 0.0

        self.pending_review_reports = Report.objects.filter(
            requires_admin_review=True
        ).count()
        
        # المطابقة
        self.total_matches = MatchResult.objects.count()
        self.new_matches = MatchResult.objects.filter(
            detected_at__date=stats_date
        ).count()
        
        self.accepted_matches = MatchResult.objects.filter(
            match_status='accepted'
        ).count()
        
        self.false_positive_matches = MatchResult.objects.filter(
            match_status='false_positive'
        ).count()
        
        # حساب معدل نجاح المطابقة
        total_accepted = MatchResult.objects.filter(
            match_status='accepted'
        ).count()
        
        total_reviewed = MatchResult.objects.filter(
            match_status__in=['accepted', 'rejected', 'false_positive']
        ).count()
        
        # جلب إحصائيات من التقارير مباشرة لضمان الدقة
        self.resolved_reports = Report.objects.filter(status='resolved').count()
        self.missing_reports = Report.objects.filter(report_type='missing').count()
        self.found_reports = Report.objects.filter(report_type='found').count()
        self.total_reports = Report.objects.count()
        self.total_users = User.objects.count()
        
        if total_reviewed > 0:
            self.match_success_rate = (total_accepted / total_reviewed) * 100
        else:
            # قيمة افتراضية منطقية بدلاً من 85% الثابتة، نحسبها من إجمالي البلاغات المحلولة
            if self.total_reports > 0:
                self.match_success_rate = (self.resolved_reports / self.total_reports) * 100
            else:
                self.match_success_rate = 0.0
        
        # الجغرافيا
        # أهم المدن
        from django.db.models import Count
        city_stats = Report.objects.filter(
            city__isnull=False
        ).values('city').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        # ملاحظة: تم التأكد من أن الترتيب الافتراضي لا يتعارض مع التجميع في SQL Server
        # بوضع order_by بعد annotate
        
        self.top_cities = [
            {'city': item['city'], 'count': item['count']}
            for item in city_stats
        ]
        
        # البلاغات حسب الجنس
        gender_stats = Report.objects.values('gender').order_by().annotate(
            count=Count('id')
        )
        self.reports_by_gender = {
            item['gender']: item['count']
            for item in gender_stats
        }
        
        # البلاغات حسب الفئة العمرية
        age_groups = {
            'children': (0, 12),
            'teens': (13, 19),
            'young_adults': (20, 35),
            'adults': (36, 60),
            'seniors': (61, 150)
        }
        
        age_stats = {}
        for group, (min_age, max_age) in age_groups.items():
            count = Report.objects.filter(
                age__gte=min_age,
                age__lte=max_age
            ).count()
            age_stats[group] = count
        
        self.reports_by_age_group = age_stats
        
        self.save()


class PerformanceMetric(models.Model):
    """مقاييس الأداء"""
    metric_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    metric_name = models.CharField(_('اسم المقياس'), max_length=100, unique=True)
    metric_description = models.TextField(_('وصف المقياس'), blank=True)
    
    # القيم
    current_value = models.FloatField(_('القيمة الحالية'), default=0.0)
    target_value = models.FloatField(_('القيمة المستهدفة'), default=100.0)
    min_value = models.FloatField(_('القيمة الدنيا'), default=0.0)
    max_value = models.FloatField(_('القيمة القصوى'), default=100.0)
    
    # الوحدة
    unit = models.CharField(_('الوحدة'), max_length=50, default='%')
    
    # الفئة
    category = models.CharField(
        _('الفئة'),
        max_length=50,
        choices=[
            ('system', 'نظام'),
            ('matching', 'مطابقة'),
            ('user', 'مستخدم'),
            ('report', 'بلاغ'),
            ('security', 'أمان'),
        ],
        default='system'
    )
    
    # الاتجاه
    direction = models.CharField(
        _('الاتجاه'),
        max_length=20,
        choices=[
            ('higher_better', 'الأعلى أفضل'),
            ('lower_better', 'الأقل أفضل'),
            ('target', 'الهدف أفضل'),
        ],
        default='higher_better'
    )
    
    # التحديث
    last_updated = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    update_frequency = models.CharField(
        _('تكرار التحديث'),
        max_length=20,
        choices=[
            ('realtime', 'حقيقي'),
            ('hourly', 'كل ساعة'),
            ('daily', 'يومي'),
            ('weekly', 'أسبوعي'),
        ],
        default='daily'
    )
    
    # الحالة
    is_active = models.BooleanField(_('نشط'), default=True)
    threshold_warning = models.FloatField(_('عتبة التحذير'), default=70.0)
    threshold_critical = models.FloatField(_('عتبة الخطير'), default=50.0)
    
    class Meta:
        verbose_name = _('مقياس أداء')
        verbose_name_plural = _('مقاييس الأداء')
        ordering = ['category', 'metric_name']
    
    def __str__(self):
        return f"{self.metric_name} ({self.current_value}{self.unit})"
    
    def get_status(self):
        """الحصول على حالة المقياس"""
        percentage = (self.current_value / self.target_value) * 100
        
        if percentage >= self.threshold_warning:
            return 'healthy', 'صحي'
        elif percentage >= self.threshold_critical:
            return 'warning', 'تحذير'
        else:
            return 'critical', 'خطير'
    
    def get_percentage(self):
        """الحصول على النسبة المئوية"""
        if self.target_value == 0:
            return 0.0
        return (self.current_value / self.target_value) * 100


class AnalyticsReport(models.Model):
    """تقارير تحليلية"""
    report_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    report_name = models.CharField(_('اسم التقرير'), max_length=200)
    report_type = models.CharField(
        _('نوع التقرير'),
        max_length=50,
        choices=[
            ('performance', 'أداء'),
            ('user', 'مستخدمين'),
            ('reports', 'بلاغات'),
            ('matching', 'مطابقة'),
            ('financial', 'مالي'),
            ('custom', 'مخصص'),
        ],
        default='performance'
    )
    
    # المحتوى
    description = models.TextField(_('الوصف'), blank=True)
    filters = models.JSONField(_('الفلاتر'), blank=True, null=True)
    
    # البيانات
    data = models.JSONField(_('البيانات'), blank=True, null=True)
    charts = models.JSONField(_('الرسوم البيانية'), blank=True, null=True)
    insights = models.TextField(_('الرؤى والتحليلات'), blank=True)
    recommendations = models.TextField(_('التوصيات'), blank=True)
    
    # التوقيت
    period_start = models.DateField(_('بداية الفترة'))
    period_end = models.DateField(_('نهاية الفترة'))
    generated_at = models.DateTimeField(_('تاريخ التوليد'), auto_now_add=True)
    
    # التكوين
    is_scheduled = models.BooleanField(_('مجدول'), default=False)
    schedule_frequency = models.CharField(
        _('تكرار الجدولة'),
        max_length=20,
        choices=[
            ('daily', 'يومي'),
            ('weekly', 'أسبوعي'),
            ('monthly', 'شهري'),
            ('quarterly', 'ربع سنوي'),
            ('yearly', 'سنوي'),
        ],
        blank=True
    )
    
    # التصدير
    export_formats = models.JSONField(
        _('صيغ التصدير'),
        default=list,
        help_text='قائمة الصيغ المدعومة: [pdf, excel, csv, json]'
    )
    
    # التحديث
    last_run = models.DateTimeField(_('آخر تشغيل'), null=True, blank=True)
    next_run = models.DateTimeField(_('التشغيل التالي'), null=True, blank=True)
    
    # الحالة
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=[
            ('draft', 'مسودة'),
            ('generating', 'قيد التوليد'),
            ('ready', 'جاهز'),
            ('failed', 'فشل'),
            ('archived', 'مؤرشف'),
        ],
        default='draft'
    )
    
    # الإعدادات
    is_public = models.BooleanField(_('عام'), default=False)
    allowed_users = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_('المستخدمون المسموح لهم'),
        help_text='المستخدمون الذين يمكنهم رؤية هذا التقرير'
    )
    
    class Meta:
        verbose_name = _('تقرير تحليلي')
        verbose_name_plural = _('التقارير التحليلية')
        ordering = ['-generated_at']
    
    def __str__(self):
        return self.report_name
    
    def generate_report(self):
        """توليد التقرير"""
        try:
            self.status = 'generating'
            self.save()
            
            # توليد البيانات حسب نوع التقرير
            if self.report_type == 'performance':
                self.data = self._generate_performance_report()
            elif self.report_type == 'user':
                self.data = self._generate_user_report()
            elif self.report_type == 'reports':
                self.data = self._generate_reports_report()
            elif self.report_type == 'matching':
                self.data = self._generate_matching_report()
            
            # توليد الرؤى والتوصيات
            self.insights = self._generate_insights()
            self.recommendations = self._generate_recommendations()
            
            self.status = 'ready'
            self.last_run = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            self.status = 'failed'
            self.insights = f"خطأ في توليد التقرير: {str(e)}"
            self.save()
            return False
    
    def _generate_performance_report(self):
        """توليد تقرير الأداء"""
        from datetime import timedelta
        
        end_date = self.period_end
        start_date = self.period_start
        
        # الحصول على الإحصائيات اليومية للفترة
        daily_stats = DailyStats.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        data = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'summary': {
                'total_reports': sum(stat.new_reports for stat in daily_stats),
                'total_matches': sum(stat.new_matches for stat in daily_stats),
                'total_users': sum(stat.new_users for stat in daily_stats),
                'avg_match_success_rate': sum(stat.match_success_rate for stat in daily_stats) / len(daily_stats) if daily_stats else 0,
            },
            'daily_data': [
                {
                    'date': stat.date.isoformat(),
                    'new_reports': stat.new_reports,
                    'new_matches': stat.new_matches,
                    'new_users': stat.new_users,
                    'match_success_rate': stat.match_success_rate,
                }
                for stat in daily_stats
            ],
            'metrics': list(PerformanceMetric.objects.filter(is_active=True).values(
                'metric_name', 'current_value', 'target_value', 'unit', 'category'
            ))
        }
        
        return data


class DashboardWidget(models.Model):
    """عناصر واجهة لوحة التحكم"""
    widget_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    widget_name = models.CharField(_('اسم العنصر'), max_length=100)
    widget_type = models.CharField(
        _('نوع العنصر'),
        max_length=50,
        choices=[
            ('chart', 'رسم بياني'),
            ('metric', 'مقياس'),
            ('table', 'جدول'),
            ('list', 'قائمة'),
            ('map', 'خريطة'),
        ],
        default='metric'
    )
    
    # التكوين
    data_source = models.CharField(
        _('مصدر البيانات'),
        max_length=50,
        choices=[
            ('daily_stats', 'الإحصائيات اليومية'),
            ('performance_metrics', 'مقاييس الأداء'),
            ('reports', 'البلاغات'),
            ('users', 'المستخدمين'),
            ('matches', 'المطابقات'),
            ('custom_query', 'استعلام مخصص'),
        ],
        default='daily_stats'
    )
    
    # الاستعلام
    query = models.TextField(_('الاستعلام'), blank=True)
    filters = models.JSONField(_('الفلاتر'), blank=True, null=True)
    
    # العرض
    title = models.CharField(_('العنوان'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    size = models.CharField(
        _('الحجم'),
        max_length=20,
        choices=[
            ('small', 'صغير (1x1)'),
            ('medium', 'متوسط (2x1)'),
            ('large', 'كبير (2x2)'),
            ('full', 'كامل (3x2)'),
        ],
        default='medium'
    )
    
    # الموقع
    column = models.IntegerField(_('العمود'), default=1)
    row = models.IntegerField(_('الصف'), default=1)
    order = models.IntegerField(_('الترتيب'), default=0)
    
    # الإعدادات
    refresh_interval = models.IntegerField(
        _('فترة التحديث (ثواني)'),
        default=300,
        help_text='0 = لا يتم التحديث تلقائياً'
    )
    
    # الوصول
    allowed_roles = models.JSONField(
        _('الأدوار المسموحة'),
        default=list,
        help_text='قائمة الأدوار التي يمكنها رؤية هذا العنصر'
    )
    
    # الحالة
    is_active = models.BooleanField(_('نشط'), default=True)
    is_public = models.BooleanField(_('عام'), default=False)
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('عنصر لوحة تحكم')
        verbose_name_plural = _('عناصر لوحة التحكم')
        ordering = ['column', 'row', 'order']
    
    def __str__(self):
        return self.widget_name
    
    def get_data(self, user=None):
        """الحصول على بيانات العنصر"""
        if self.data_source == 'daily_stats':
            stats = DailyStats.get_or_create_today()
            return {
                'new_reports': stats.new_reports,
                'new_matches': stats.new_matches,
                'new_users': stats.new_users,
                'match_success_rate': stats.match_success_rate,
            }
        
        elif self.data_source == 'performance_metrics':
            metrics = PerformanceMetric.objects.filter(
                is_active=True,
                category='system'
            ).values('metric_name', 'current_value', 'target_value', 'unit')
            return list(metrics)
        
        elif self.data_source == 'reports':
            from reports.models import Report
            from django.db.models import Count
            data = Report.objects.aggregate(
                total=Count('id'),
                missing=Count('id', filter=models.Q(report_type='missing')),
                found=Count('id', filter=models.Q(report_type='found')),
                active=Count('id', filter=models.Q(status='active')),
                resolved=Count('id', filter=models.Q(status='resolved')),
            )
            return data
            
        elif self.data_source == 'matches':
            from matching.models import MatchResult
            from django.db.models import Count, Avg
            
            data = MatchResult.objects.aggregate(
                total=Count('id'),
                pending=Count('id', filter=models.Q(match_status='pending')),
                accepted=Count('id', filter=models.Q(match_status='accepted')),
                avg_similarity=Avg('similarity_score'),
            )
            return data
        
        return {}


class RequestLog(models.Model):
    """سجل طلبات النظام"""
    method = models.CharField(_('طريقة الطلب'), max_length=10)
    path = models.CharField(_('المسار'), max_length=500)
    status_code = models.IntegerField(_('رمز الحالة'))
    processing_time = models.FloatField(_('وقت المعالجة'))
    user_agent = models.TextField(_('معلومات المتصفح'), blank=True)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    query_params = models.JSONField(_('معاملات الاستعلام'), default=dict, blank=True)
    user_id = models.IntegerField(_('معرف المستخدم'), null=True, blank=True)
    response_size = models.IntegerField(_('حجم الرد'), default=0)
    slow_queries = models.JSONField(_('الاستعلامات البطيئة'), default=list, blank=True)
    created_at = models.DateTimeField(_('تاريخ الطلب'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل طلب')
        verbose_name_plural = _('سجل الطلبات')
        ordering = ['-created_at']
