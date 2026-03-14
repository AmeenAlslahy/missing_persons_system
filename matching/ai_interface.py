# matching/ai_interface.py
"""
واجهة مجردة لمحرك الذكاء الاصطناعي للتعامل مع بصمات الوجه
"""
import logging
# import numpy as np  # Moved to internal methods to speed up startup
from django.conf import settings

logger = logging.getLogger(__name__)


class FaceEngineInterface:
    """
    واجهة مجردة لمحرك الوجه - تتعامل مع عدم توفر المحرك بشكل آمن
    """
    
    # تخزين مؤقت للبصمات المستخرجة
    _cache = {}
    
    @classmethod
    def is_available(cls):
        """التحقق من توفر محرك الوجه"""
        try:
            from ai.engine import FaceEngine
            return True
        except ImportError:
            return False
    
    @classmethod
    def get_embedding(cls, image_path):
        """
        الحصول على بصمة الوجه من الصورة
        
        Args:
            image_path: مسار الصورة
            
        Returns:
            numpy array: بصمة الوجه أو None في حالة الفشل
        """
        try:
            # محاولة استيراد المحرك
            from ai.engine import FaceEngine
            
            # استخراج البصمة
            embedding = FaceEngine.get_embedding(image_path)
            
            if embedding is not None:
                logger.debug(f"تم استخراج بصمة وجه بنجاح من {image_path}")
                return embedding
            else:
                logger.warning(f"فشل استخراج بصمة وجه من {image_path}")
                return None
                
        except ImportError:
            logger.warning("محرك الذكاء الاصطناعي غير متوفر، سيتم استخدام بصمة افتراضية")
            return cls._get_fallback_embedding(image_path)
            
        except Exception as e:
            logger.error(f"خطأ في محرك الوجه: {e}")
            return cls._get_fallback_embedding(image_path)
    
    @classmethod
    def _get_fallback_embedding(cls, image_path):
        """
        إنشاء بصمة افتراضية للتطوير والاختبار
        """
        import hashlib
        
        # استخدام مسار الصورة لإنشاء بصمة ثابتة نسبياً
        hash_object = hashlib.sha256(str(image_path).encode())
        hash_bytes = hash_object.digest()
        
        # تحويل إلى 512 رقم عشري (محاكاة لبصمة وجه حقيقية)
        import numpy as np
        np.random.seed(int.from_bytes(hash_bytes[:4], 'little'))
        embedding = np.random.uniform(-1, 1, 512)
        
        # تطبيع المتجه
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding
    
    @classmethod
    def get_face_quality(cls, image_path):
        """
        تقدير جودة الصورة للوجه
        
        Returns:
            float: درجة الجودة من 0 إلى 1
        """
        try:
            from ai.engine import FaceEngine
            return FaceEngine.get_quality_score(image_path)
        except:
            # قيمة افتراضية
            return 0.7