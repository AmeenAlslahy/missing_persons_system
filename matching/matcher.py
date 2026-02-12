import json
import numpy as np
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import logging

from reports.models import Report, ReportImage
from .models import FaceEmbedding, MatchResult, MatchingConfig, MatchingAuditLog

logger = logging.getLogger(__name__)


class FaceMatcher:
    """مطابقة الوجوه باستخدام الذكاء الاصطناعي"""
    
    def __init__(self):
        self.config = self.get_config()
    
    def get_config(self):
        """الحصول على إعدادات المطابقة"""
        config, _ = MatchingConfig.objects.get_or_create(
            config_name='default',
            defaults={
                'similarity_threshold': 0.32,
                'confidence_threshold': 70.0,
                'enable_face_matching': True,
                'ai_model_version': 'MobileNetV2_v1.0',
            }
        )
        return config
    
    def calculate_similarity(self, embedding1, embedding2):
        """حساب تشابه جيب التمام (Cosine Similarity) المتوافق مع محرك Siamese"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # التحقق من التطابق التام
            if np.array_equal(vec1, vec2):
                return 1.0
                
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 < 1e-9 or norm2 < 1e-9: 
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            
            # محرك السيامي لدينا يعمل بعتبة 0.32 للتشابه الخام
            # لكننا نحولها لمقياس [0, 1] للعرض في الواجهة
            # نحافظ على القيمة الخام للحسابات الداخلية إذا لزم الأمر
            return float(similarity)
        except Exception as e:
            logger.error(f"خطأ في حساب التشابه: {e}")
            return 0.0
    
    def calculate_confidence(self, similarity_score, quality_score1, quality_score2):
        """حساب درجة الثقة بناءً على التشابه وجودة الصور"""
        avg_quality = (quality_score1 + quality_score2) / 2
        base_confidence = similarity_score * 100
        quality_factor = 1.0
        if avg_quality > 0.8: quality_factor = 1.2
        elif avg_quality < 0.4: quality_factor = 0.5
        return min(base_confidence * quality_factor, 100.0)
    
    def match_single_pair(self, missing_report, found_report):
        """مطابقة زوج واحد (مفقود + معثور عليه) باستخدام الصور"""
        try:
            # دالة مساعدة لاستخراج البصمات من الكائنات المحملة مسبقاً (Prefetched)
            def get_valid_embeddings(report):
                embeddings = []
                # استخدام .all() للاستفادة من الكاش إذا تم استخدام prefetch_related
                for img in report.images.all():
                    if img.face_detected:
                        # محاولة الوصول للعلاقة العكسية OneToOne
                        # قد تثير DoesNotExist إذا لم تكن موجودة و لم يتم تحميلها، لكن مع prefetch ستكون None أو كائن
                        try:
                            if hasattr(img, 'face_embedding_obj'):
                                emb = img.face_embedding_obj
                                if emb and emb.processing_status == 'completed':
                                    embeddings.append(emb)
                        except Exception:
                            pass
                return embeddings

            missing_embeddings = get_valid_embeddings(missing_report)
            found_embeddings = get_valid_embeddings(found_report)
            
            if not missing_embeddings or not found_embeddings: return 0.0, 0.0
            
            best_similarity = 0.0
            best_m_emb = None
            best_f_emb = None
            
            # المقارنة في الذاكرة (سريعة جداً لأن المصفوفات numpy)
            for m_emb in missing_embeddings:
                for f_emb in found_embeddings:
                    sim = self.calculate_similarity(m_emb.embedding_vector, f_emb.embedding_vector)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_m_emb = m_emb
                        best_f_emb = f_emb
            
            if best_m_emb and best_f_emb:
                conf = self.calculate_confidence(best_similarity, best_m_emb.quality_score, best_f_emb.quality_score)
                return best_similarity, conf
            return 0.0, 0.0
        except Exception as e:
            logger.error(f"خطأ في مطابقة الزوج: {e}")
            return 0.0, 0.0


class ReportMatcher:
    """محرك المطابقة الهجين (وجه + بيانات)"""
    
    def __init__(self):
        self.face_matcher = FaceMatcher()
        self.config = self.face_matcher.config

    def match_by_location(self, report1, report2):
        """مطابقة الموقع الجغرافي"""
        score = 0.0
        # مطابقة المدينة
        if report1.city and report2.city and report1.city == report2.city:
            score += 0.5
        # مطابقة الحي
        if report1.district and report2.district and report1.district == report2.district:
            score += 0.5
        return score

    def match_by_features(self, report1, report2):
        """مطابقة الصفات الجسدية"""
        matches = 0
        total_criteria = 0
        
        # الجنس (إلزامي للمطابقة المنطقية)
        if report1.gender != report2.gender and report1.gender != 'U' and report2.gender != 'U':
            return 0.0 # تناقض في الجنس
            
        features = [
            ('eye_color', 0.2),
            ('hair_color', 0.2),
            ('skin_color', 0.2),
            ('age_group', 0.4)
        ]
        
        feature_score = 0.0
        for attr, weight in features:
            val1 = getattr(report1, attr, None)
            val2 = getattr(report2, attr, None)
            if val1 and val2:
                total_criteria += weight
                if val1 == val2:
                    feature_score += weight
                    
        return feature_score / total_criteria if total_criteria > 0 else 0.5
    
    def match_by_name(self, name1, name2):
        """مقارنة الأسماء باستخدام التشابه النصي"""
        if not name1 or not name2:
            return 0.0
        
        # تنظيف الأسماء
        name1 = name1.strip().lower()
        name2 = name2.strip().lower()
        
        # تطابق تام
        if name1 == name2:
            return 1.0
        
        # تطابق جزئي - إذا كان أحد الأسماء يحتوي على الآخر
        if name1 in name2 or name2 in name1:
            return 0.8
        
        # حساب التشابه بناءً على الكلمات المشتركة
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return 0.0
        
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        similarity = len(common_words) / len(total_words) if total_words else 0.0
        
        return similarity

    def calculate_hybrid_score(self, report1, report2):
        """حساب درجة المطابقة الهجينة مع تفاصيل توضيحية"""
        # الحسابات
        face_sim, face_conf = self.face_matcher.match_single_pair(report1, report2)
        name_score = self.match_by_name(report1.person_name, report2.person_name)
        location_score = self.match_by_location(report1, report2)
        feature_score = self.match_by_features(report1, report2)
        
        # إذا كان هناك تناقض صارخ في الصفات المحددة، نضعف النتيجة
        if feature_score == 0 and (report1.gender != report2.gender):
            return 0.0, 0.0, {}

        # الأوزان (قابلة للتعديل من الإعدادات)
        # الافتراضي: وجه (0.6)، اسم (0.2)، موقع (0.1)، صفات (0.1)
        weights = {
            'face': 0.6,
            'name': 0.2,
            'location': 0.1,
            'features': 0.1
        }
        
        hybrid_similarity = (
            (face_sim * weights['face']) +
            (name_score * weights['name']) +
            (location_score * weights['location']) +
            (feature_score * weights['features'])
        )
        
        # الثقة تعتمد بشكل أساسي على الوجه إذا وجد، وإلا على الاسم والصفات
        if face_conf > 0:
            hybrid_confidence = face_conf
        else:
            hybrid_confidence = (name_score * 0.7 + feature_score * 0.3) * 100

        details = {
            'face_similarity': round(face_sim, 2),
            'name_match': round(name_score, 2),
            'location_match': round(location_score, 2),
            'feature_match': round(feature_score, 2),
            'explanation': self._generate_explanation(face_sim, name_score, location_score, feature_score)
        }
        
        return hybrid_similarity, hybrid_confidence, details

    def _generate_explanation(self, face, name, loc, feat):
        reasons = []
        if face > 0.8: reasons.append("تطابق عالي جداً في ملامح الوجه")
        elif face > 0.5: reasons.append("تشابه في ملامح الوجه")
        
        if name > 0.8: reasons.append("تطابق في الاسم")
        elif name > 0.4: reasons.append("تشابه جزئي في الأسماء")
        
        if loc > 0.5: reasons.append("رصد في نفس المنطقة الجغرافية")
        if feat > 0.7: reasons.append("تشابه كبير في الصفات الجسدية")
        
        return " + ".join(reasons) if reasons else "تقارب في البيانات العامة"

    def run_matching_for_report(self, report):
        """تشغيل المطابقة لبلاغ محدد فوراً"""
        if report.status != 'active':
            return 0
            
        # إعادة تحميل البلاغ مع البيانات المرتبطة لضمان السرعة
        # نستخدم prefetch_related لجلب الصور والبصمات في استعلام واحد
        try:
            report_with_data = Report.objects.select_related('user').prefetch_related(
                'images',
                'images__face_embedding_obj'
            ).get(id=report.id)
        except Report.DoesNotExist:
            return 0

        # تحديد البلاغات المقابلة
        target_type = 'found' if report.report_type == 'missing' else 'missing'
        
        # جلب البلاغات الهدف مع بياناتها دفعة واحدة
        target_reports = Report.objects.filter(
            report_type=target_type,
            status='active'
        ).exclude(id=report.id).prefetch_related(
            'images',
            'images__face_embedding_obj'
        )
        
        matches_count = 0
        for target in target_reports:
            similarity, confidence, details = self.calculate_hybrid_score(report_with_data, target)
            
            if similarity >= self.config.similarity_threshold or confidence >= self.config.confidence_threshold:
                # حفظ النتيجة
                MatchResult.objects.get_or_create(
                    missing_report=report if report.report_type == 'missing' else target,
                    found_report=target if report.report_type == 'missing' else report,
                    defaults={
                        'similarity_score': similarity,
                        'confidence_score': confidence,
                        'match_type': MatchResult.MatchType.AUTO,
                        'match_status': MatchResult.MatchStatus.PENDING,
                        'match_details': {
                            'hybrid_details': details,
                            'matching_version': 'v2.0_hybrid'
                        }
                    }
                )
                matches_count += 1
                
                # تسجيل اكتشاف المطابقة
                MatchingAuditLog.objects.create(
                    action_type='MATCH_FOUND',
                    action_details=f'تطابق هجين: {report.person_name} - {target.person_name}',
                    metadata={'similarity': similarity, 'confidence': confidence}
                )
        
        return matches_count
