from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

class Governorate(models.Model):
    name = models.CharField(_('اسم المحافظة'), max_length=100, unique=True)
    name_ar = models.CharField(_('الاسم بالعربية'), max_length=100, null=True, blank=True)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True, null=True)
    code = models.CharField(_('كود المحافظة'), max_length=10, unique=True, blank=True, null=True)
    population = models.IntegerField(_('عدد السكان'), blank=True, null=True)
    area = models.FloatField(_('المساحة (كم²)'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True, null=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)

    class Meta:
        verbose_name = _('محافظة')
        verbose_name_plural = _('المحافظات')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name_ar or self.name or str(_("محافظة غير معروفة"))

    def save(self, *args, **kwargs):
        cache.delete('governorates_list')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        cache.delete('governorates_list')
        super().delete(*args, **kwargs)

    @property
    def districts_count(self):
        """عدد المديريات في المحافظة"""
        return self.districts.filter(is_active=True).count()


class District(models.Model):
    governorate = models.ForeignKey(Governorate, on_delete=models.CASCADE, related_name='districts', verbose_name=_('المحافظة'))
    name = models.CharField(_('اسم المديرية'), max_length=100)
    name_ar = models.CharField(_('الاسم بالعربية'), max_length=100, null=True, blank=True)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True, null=True)
    code = models.CharField(_('كود المديرية'), max_length=10, blank=True, null=True)
    population = models.IntegerField(_('عدد السكان'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True, null=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مديرية')
        verbose_name_plural = _('المديريات')
        ordering = ['governorate__order', 'order', 'name']
        unique_together = ['governorate', 'name']

    def __str__(self):
        gov_name = self.governorate.name_ar or self.governorate.name or str(_("محافظة غير معروفة"))
        dist_name = self.name_ar or self.name or str(_("مديرية غير معروفة"))
        return f"{dist_name} - {gov_name}"

    def save(self, *args, **kwargs):
        if self.pk:
            cache.delete(f'district_{self.pk}')
        if self.governorate_id:
            cache.delete(f'districts_gov_{self.governorate_id}')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk:
            cache.delete(f'district_{self.pk}')
        if self.governorate_id:
            cache.delete(f'districts_gov_{self.governorate_id}')
        super().delete(*args, **kwargs)

    @property
    def uzlahs_count(self):
        """عدد العزل في المديرية"""
        return self.uzlahs.filter(is_active=True).count()


class Uzlah(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='uzlahs', verbose_name=_('المديرية'))
    name = models.CharField(_('اسم العزلة'), max_length=100)
    name_ar = models.CharField(_('الاسم بالعربية'), max_length=100, null=True, blank=True)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True, null=True)
    code = models.CharField(_('كود العزلة'), max_length=10, blank=True, null=True)
    population = models.IntegerField(_('عدد السكان'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True, null=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)

    class Meta:
        verbose_name = _('عزلة')
        verbose_name_plural = _('العزل')
        ordering = ['district__order', 'order', 'name']
        unique_together = ['district', 'name']

    def __str__(self):
        dist_name = self.district.name_ar or self.district.name or str(_("مديرية غير معروفة"))
        uzlah_name = self.name_ar or self.name or str(_("عزلة غير معروفة"))
        return f"{uzlah_name} - {dist_name}"

    def save(self, *args, **kwargs):
        if self.pk:
            cache.delete(f'uzlah_{self.pk}')
        if self.district_id:
            cache.delete(f'uzlahs_dist_{self.district_id}')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk:
            cache.delete(f'uzlah_{self.pk}')
        if self.district_id:
            cache.delete(f'uzlahs_dist_{self.district_id}')
        super().delete(*args, **kwargs)
