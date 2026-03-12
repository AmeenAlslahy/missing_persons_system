from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import logging

from reports.models import Report, ReportImage
from .models import MatchResult, MatchingAuditLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReportImage)
def create_face_embedding(sender, instance, created, **kwargs):
    """
    إنشاء بصمة وجه عند رفع صورة جديدة
    """
    if not created:
        return
    
    # محاولة استيراد محرك الوجه بشكل آمن
    try:
        from ai.engine import FaceEngine
    except ImportError:
        logger.warning("FaceEngine غير متوفر، سيتم استخدام بصمة افتراضية")
        FaceEngine = None
    
    def process_image():
        """معالجة الصورة في خلفية"""
        try:
            embedding_vector = None
            quality_score = 0.5
            
            if FaceEngine and instance.image_path:
                try:
                    # محاولة استخراج البصمة من مسار الصورة
                    if hasattr(instance.image_path, 'path'):
                        vector = FaceEngine.get_embedding(instance.image_path.path)
                        if vector is not None:
                            embedding_vector = vector.tolist()
                            quality_score = 0.8  # يمكن تحسينه لاحقاً
                except Exception as e:
                    logger.error(f"خطأ في محرك الذكاء الاصطناعي: {e}")

            # إذا فشل المحرك أو لم يتوفر، نستخدم بصمة افتراضية
            if embedding_vector is None:
                # استخدام بصمة عشوائية ثابتة للتطوير فقط
                import random
                embedding_vector = [random.uniform(-1, 1) for _ in range(512)]
                quality_score = 0.5
            
            # تحديث الصورة
            instance.face_embedding = embedding_vector
            instance.quality_score = quality_score
            instance.save(update_fields=['face_embedding', 'quality_score'])
            
            # تشغيل المطابقة بعد اكتمال البصمة
            if instance.report and instance.report.status == 'active':
                from .matcher import ReportMatcher
                matcher = ReportMatcher()
                matcher.run_matching_for_report(instance.report)
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الصورة: {e}")
    
    # تنفيذ بعد commit لضمان حفظ الصورة
    transaction.on_commit(process_image)


@receiver(post_save, sender=Report)
def trigger_matching_on_report_update(sender, instance, created, **kwargs):
    """
    تشغيل المطابقة عند إنشاء أو تحديث بلاغ
    """
    # نتجنب التشغيل عند الإنشاء لأن signal الصورة سيتولى الأمر
    if created:
        return
    
    # نشغل المطابقة فقط إذا تغيرت الحالة إلى active
    update_fields = kwargs.get('update_fields')
    if (update_fields is None or 'status' in update_fields) and instance.status == 'active':
        
        def run_matching():
            try:
                from .matcher import ReportMatcher
                matcher = ReportMatcher()
                matches_count = matcher.run_matching_for_report(instance)
                
                if matches_count > 0:
                    logger.info(f"تم العثور على {matches_count} مطابقة للبلاغ {instance.report_code}")
                    
            except Exception as e:
                logger.error(f"فشل تشغيل المطابقة للبلاغ {instance.report_code}: {e}")
        
        transaction.on_commit(run_matching)