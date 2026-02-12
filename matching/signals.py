from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from reports.models import Report, ReportImage
from .models import FaceEmbedding, MatchingConfig

import sys
import os
from django.conf import settings

# إضافة مجلد src للمسار لتمكين استيراد محرك الذكاء الاصطناعي
# إضافة مجلد ai للمسار لتمكين استيراد محرك الذكاء الاصطناعي
ai_path = os.path.join(settings.BASE_DIR, 'ai')
if ai_path not in sys.path:
    sys.path.append(ai_path)

try:
    from engine import FaceEngine
except ImportError:
    FaceEngine = None
    import logging
    import traceback
    traceback.print_exc()
    logging.getLogger(__name__).error(f"Could not import FaceEngine from ai.engine: {ImportError}")


@receiver(post_save, sender=ReportImage)
def create_face_embedding(sender, instance, created, **kwargs):
    """
    إنشاء بصمة وجه عند رفع صورة جديدة
    """
    if created:
        # استدعاء محرك الذكاء الاصطناعي لاستخراج البصمة الحقيقية
        embedding_vector = None
        quality_score = 0.5
        
        if FaceEngine and instance.image:
            try:
                # محاولة استخراج البصمة من مسار الصورة
                vector = FaceEngine.get_embedding(instance.image.path)
                if vector is not None:
                    embedding_vector = vector.tolist()
                    instance.face_detected = True
                    quality_score = 0.8 # يمكن تحسينه لاحقاً من المحرك
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"AI Engine Error: {e}")

        # إذا فشل المحرك أو لم يتوفر، نستخدم بصمة افتراضية (مؤقتاً للسلامة)
        if embedding_vector is None:
            embedding_vector = [0.1] * 1280
            instance.face_detected = False
        
        instance.save()
        
        emb, _ = FaceEmbedding.objects.get_or_create(
            image=instance,
            defaults={
                'embedding_vector': embedding_vector,
                'embedding_version': 'v2.0_siamese',
                'face_count': 1 if instance.face_detected else 0,
                'quality_score': quality_score,
                'confidence_score': 0.9 if instance.face_detected else 0.0,
                'processing_status': 'completed'
            }
        )
        # تشغيل المطابقة فور اكتمال البصمة
        from .matcher import ReportMatcher
        matcher = ReportMatcher()
        matcher.run_matching_for_report(instance.report)


@receiver(post_save, sender=Report)
def trigger_matching_on_report_update(sender, instance, created, **kwargs):
    """
    تشغيل المطابقة عند إنشاء أو تحديث بلاغ
    """
    if instance.status == 'active':
        # إذا كان البلاغ جديداً ويحتوي على صورة، فإن إشارة ReportImage ستتولى أمر المطابقة
        # لذا نتجاوز التشغيل هنا لتجنب التكرار وضمان وجود البصمة
        if created and instance.primary_photo:
            return

        try:
            from .matcher import ReportMatcher
            matcher = ReportMatcher()
            matcher.run_matching_for_report(instance)
        except Exception as e:
            # لا نعطل العملية الأساسية إذا فشلت المطابقة
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to run matching for report {instance.pk}: {str(e)}")
