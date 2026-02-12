from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Report, ReportImage

@receiver(post_save, sender=Report)
def sync_primary_photo_to_report_image(sender, instance, created, **kwargs):
    """
    عند حفظ بلاغ يحتوي على صورة رئيسية، نقوم بإنشاء سجل في ReportImage 
    ليتمكن نظام المطابقة من معالجتها.
    """
    if instance.primary_photo:
        # نقوم بالبحث عما إذا كان قد تم إنشاء الصورة مسبقاً لهذا البلاغ باستخدام هذا المسار
        # لتجنب التكرار عند كل عملية حفظ
        image_exists = ReportImage.objects.filter(
            report=instance, 
            image=instance.primary_photo.name
        ).exists()
        
        if not image_exists:
            ReportImage.objects.get_or_create(
                report=instance,
                image=instance.primary_photo
            )
