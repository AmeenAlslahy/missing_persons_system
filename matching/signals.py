from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction
import logging
from django.core.cache import cache

from reports.models import Report, ReportImage
from .models import MatchResult, MatchingAuditLog, MatchFeedback
from .ai_interface import FaceEngineInterface
from .matcher import FaceMatcher

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReportImage)
def create_face_embedding(sender, instance, created, **kwargs):
    """
    إنشاء بصمة وجه عند رفع صورة جديدة
    """
    if not created:
        return
    
    def process_image():
        """معالجة الصورة في خلفية"""
        try:
            # استخدام الواجهة الموحدة
            if instance.image_path:
                embedding = FaceEngineInterface.get_embedding(instance.image_path.path)
                quality = FaceEngineInterface.get_face_quality(instance.image_path.path)
                
                if embedding is not None:
                    # تحويل numpy array إلى قائمة للتخزين في JSON
                    if hasattr(embedding, 'tolist'):
                        instance.face_embedding = embedding.tolist()
                    else:
                        instance.face_embedding = embedding
                    
                    instance.quality_score = quality
                    instance.save(update_fields=['face_embedding', 'quality_score'])
                    
                    # مسح الكاش لهذا البلاغ
                    if instance.report_id:
                        face_matcher = FaceMatcher()
                        face_matcher.invalidate_cache(instance.report_id)
                    
                    logger.info(f"تم إنشاء بصمة وجه للصورة {instance.image_id}")
                    
                    # تشغيل المطابقة بعد اكتمال البصمة
                    if instance.report and instance.report.status == 'active':
                        from .matcher import ReportMatcher
                        matcher = ReportMatcher()
                        matches_count = matcher.run_matching_for_report(instance.report)
                        
                        if matches_count > 0:
                            logger.info(f"تم العثور على {matches_count} مطابقة للبلاغ {instance.report.report_code}")
                else:
                    logger.warning(f"فشل إنشاء بصمة وجه للصورة {instance.image_id}")
                    
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


@receiver(post_save, sender=MatchResult)
def notify_on_high_priority_match(sender, instance, created, **kwargs):
    """إرسال إشعارات للمطابقات عالية الأولوية"""
    if created and instance.priority_level in ['urgent', 'high']:
        try:
            from notifications.services import NotificationService
            
            NotificationService.notify_admins(
                title="مطابقة جديدة عالية الأولوية",
                message=f"تم العثور على مطابقة جديدة بنسبة {int(instance.similarity_score * 100)}% بين {instance.report_1.person.full_name} و {instance.report_2.person.full_name}",
                link=f"/admin-dashboard/matches/{instance.match_id}/"
            )
        except ImportError:
            logger.warning("خدمة الإشعارات غير متوفرة")
        except Exception as e:
            logger.error(f"خطأ في إرسال الإشعارات: {e}")


@receiver(post_save, sender=MatchFeedback)
def update_match_accuracy(sender, instance, **kwargs):
    """تحديث دقة المطابقة بناءً على تقييمات المستخدمين"""
    try:
        match = instance.match
        feedback_count = match.feedback.count()
        
        if feedback_count >= 3:  # إذا كان هناك 3 تقييمات على الأقل
            correct_count = match.feedback.filter(is_correct=True).count()
            accuracy = (correct_count / feedback_count) * 100
            
            # يمكن تخزين هذه المعلومة في match_details
            details = match.match_details or {}
            details['user_accuracy'] = round(accuracy, 1)
            details['feedback_count'] = feedback_count
            match.match_details = details
            match.save(update_fields=['match_details'])
            
    except Exception as e:
        logger.error(f"خطأ في تحديث دقة المطابقة: {e}")


@receiver(post_delete, sender=ReportImage)
def clear_embedding_cache(sender, instance, **kwargs):
    """مسح الكاش عند حذف صورة"""
    if instance.report_id:
        face_matcher = FaceMatcher()
        face_matcher.invalidate_cache(instance.report_id)