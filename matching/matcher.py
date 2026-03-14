import json
import numpy as np
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, date
import logging
import re
import jellyfish
from django.core.cache import cache

from reports.models import Report, ReportImage
from .models import MatchResult, MatchingAuditLog, MatchFeedback
from .ai_interface import FaceEngineInterface

logger = logging.getLogger(__name__)


class MatchingConfig:
    """إعدادات المطابقة - يمكن جلبها من قاعدة البيانات"""
    
    def __init__(self):
        # يمكن جلب هذه القيم من نموذج الإعدادات في المستقبل
        self.similarity_threshold = 0.32
        self.confidence_threshold = 70.0
        self.enable_face_matching = True
        self.ai_model_version = 'MobileNetV2_v1.0'
        self.weights = {
            'name': 0.4,
            'face': 0.4,
            'location': 0.1,
            'features': 0.1
        }
        self.cache_timeout = 60 * 60 * 24  # 24 ساعة


class ArabicNameMatcher:
    """مطابقة متخصصة للأسماء العربية"""
    
    # أنماط الأسماء العربية الشائعة
    COMMON_PATTERNS = {
        'عبد': ['عبدالله', 'عبدالرحمن', 'عبدالعزيز', 'عبداللطيف', 'عبدالرؤوف'],
        'أبو': ['أبوبكر', 'أبوبكر', 'أبو بكر'],
        'آل': ['آلسعود', 'آل الشيخ', 'آل ثاني'],
        'بن': ['بني', 'بنت']
    }
    
    # أحرف التشابه
    SIMILAR_CHARS = {
        'ا': ['إ', 'أ', 'آ'],
        'ه': ['ة'],
        'ي': ['ى'],
        'و': ['ؤ'],
    }
    
    @classmethod
    def normalize_arabic_deep(cls, text):
        """توحيد عميق للأسماء العربية"""
        if not text:
            return ""
        
        # تحويل إلى نص
        text = str(text)
        
        # توحيد الحروف المتشابهة
        for target, sources in cls.SIMILAR_CHARS.items():
            for source in sources:
                text = text.replace(source, target)
        
        # إزالة التشكيل
        text = re.sub(r'[\u064B-\u0652]', '', text)
        
        # إزالة ال التعريف
        text = re.sub(r'^ال', '', text)
        text = re.sub(r'\s+ال', ' ', text)
        
        # إزالة المسافات الزائدة
        text = ' '.join(text.split())
        
        return text.strip()
    
    @classmethod
    def calculate_name_similarity(cls, name1, name2):
        """حساب تشابه الأسماء العربية"""
        if not name1 or not name2:
            return 0.0
        
        norm1 = cls.normalize_arabic_deep(name1)
        norm2 = cls.normalize_arabic_deep(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # استخدام خوارزمية Jaro-Winkler المناسبة للعربية
        similarity = jellyfish.jaro_winkler_similarity(norm1, norm2)
        
        # التحقق من الأنماط الشائعة
        for pattern, variants in cls.COMMON_PATTERNS.items():
            if pattern in norm1:
                for variant in variants:
                    if variant in norm2:
                        similarity = max(similarity, 0.9)
                        break
            elif pattern in norm2:
                for variant in variants:
                    if variant in norm1:
                        similarity = max(similarity, 0.9)
                        break
        
        return similarity


class FaceMatcher:
    """مطابقة الوجوه باستخدام الذكاء الاصطناعي"""
    
    def __init__(self):
        self.config = MatchingConfig()
        self.face_interface = FaceEngineInterface()
    
    def get_cached_embeddings(self, report_id):
        """الحصول على بصمات الوجه من الكاش"""
        cache_key = f'face_embeddings_{report_id}'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        # جلب من قاعدة البيانات
        images = ReportImage.objects.filter(
            report_id=report_id,
            face_embedding__isnull=False
        ).values_list('face_embedding', 'quality_score')
        
        embeddings = [(emb, qual) for emb, qual in images if emb]
        
        # تخزين في الكاش
        cache.set(cache_key, embeddings, self.config.cache_timeout)
        
        return embeddings
    
    def invalidate_cache(self, report_id):
        """مسح الكاش عند تحديث الصور"""
        cache_key = f'face_embeddings_{report_id}'
        cache.delete(cache_key)
    
    def calculate_similarity(self, embedding1, embedding2):
        """حساب تشابه جيب التمام (Cosine Similarity)"""
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
            
            # تحويل من [-1, 1] إلى [0, 1] إذا لزم الأمر
            if similarity < 0:
                similarity = 0.0
                
            return float(similarity)
        except Exception as e:
            logger.error(f"خطأ في حساب التشابه: {e}")
            return 0.0
    
    def calculate_confidence(self, similarity_score, quality_score1=None, quality_score2=None):
        """حساب درجة الثقة بناءً على التشابه وجودة الصور"""
        base_confidence = similarity_score * 100
        
        # إذا كانت جودة الصور متوفرة، نأخذها في الاعتبار
        if quality_score1 is not None and quality_score2 is not None:
            avg_quality = (quality_score1 + quality_score2) / 2
            quality_factor = 1.0
            if avg_quality > 0.8:
                quality_factor = 1.2
            elif avg_quality < 0.4:
                quality_factor = 0.5
            base_confidence *= quality_factor
        
        return min(base_confidence, 100.0)
    
    def get_confidence_level(self, confidence_score):
        """تحويل درجة الثقة إلى مستوى نصي"""
        if confidence_score >= 90:
            return 'very_high'
        elif confidence_score >= 70:
            return 'high'
        elif confidence_score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def calculate_similarity_batch(self, report1, report2):
        """حساب التشابه بين مجموعتين من الصور"""
        embeddings1 = self.get_cached_embeddings(report1.report_id)
        embeddings2 = self.get_cached_embeddings(report2.report_id)
        
        if not embeddings1 or not embeddings2:
            return 0.0, 0.0, 'low'
        
        best_similarity = 0.0
        best_quality = (0.5, 0.5)
        match_count = 0
        
        for emb1, qual1 in embeddings1:
            for emb2, qual2 in embeddings2:
                sim = self.calculate_similarity(emb1, emb2)
                if sim > best_similarity:
                    best_similarity = sim
                    best_quality = (qual1 or 0.5, qual2 or 0.5)
                if sim > 0.5:
                    match_count += 1
        
        # تحسين: إذا كان هناك عدة صور متطابقة
        if match_count > 1:
            best_similarity = min(best_similarity + 0.1, 1.0)
        
        if best_similarity > self.config.similarity_threshold:
            confidence = self.calculate_confidence(
                best_similarity, 
                best_quality[0], 
                best_quality[1]
            )
            confidence_level = self.get_confidence_level(confidence)
            return best_similarity, confidence, confidence_level
        
        return best_similarity, 0.0, 'low'


class ReportMatcher:
    """محرك المطابقة الهجين (وجه + بيانات)"""
    
    def __init__(self):
        self.face_matcher = FaceMatcher()
        self.config = self.face_matcher.config
    
    def prevent_duplicate_matches(self, report1, report2):
        """منع إنشاء مطابقات مكررة"""
        existing = MatchResult.objects.filter(
            (Q(report_1=report1) & Q(report_2=report2)) |
            (Q(report_1=report2) & Q(report_2=report1))
        ).first()
        
        if existing:
            # إذا كانت المطابقة موجودة ولم يتم رفضها
            if existing.match_status not in ['rejected', 'false_positive']:
                return existing
            # إذا كانت مرفوضة، يمكن إنشاء مطابقة جديدة إذا كانت النتيجة أفضل
            elif existing.similarity_score < 0.8:
                return None
        
        return None

    def match_by_location(self, report1, report2):
        """مطابقة الموقع الجغرافي"""
        score = 0.0
        
        # مطابقة المحافظة (موقع الفقدان)
        if hasattr(report1, 'lost_governorate') and hasattr(report2, 'lost_governorate'):
            if report1.lost_governorate and report2.lost_governorate:
                if report1.lost_governorate_id == report2.lost_governorate_id:
                    score += 0.6
                    
                    # مطابقة المديرية (إذا كانت نفس المحافظة)
                    if hasattr(report1, 'lost_district') and hasattr(report2, 'lost_district'):
                        if report1.lost_district and report2.lost_district:
                            if report1.lost_district_id == report2.lost_district_id:
                                score += 0.4
        
        return score

    def match_by_features(self, report1, report2):
        """مطابقة الصفات الجسدية"""
        if not report1.person or not report2.person:
            return 0.0
            
        person1 = report1.person
        person2 = report2.person
        
        # التحقق من الجنس (إلزامي للمطابقة المنطقية)
        if person1.gender and person2.gender and person1.gender != person2.gender:
            return 0.0  # تناقض في الجنس
            
        feature_score = 0.0
        total_weight = 0.0
        
        features = [
            ('eye_color', 0.25),
            ('hair_color', 0.25),
            ('skin_color', 0.25),
            ('body_build', 0.25)
        ]
        
        for attr, weight in features:
            val1 = getattr(person1, attr, None)
            val2 = getattr(person2, attr, None)
            if val1 and val2:
                total_weight += weight
                if val1 == val2:
                    feature_score += weight
        
        # مطابقة العمر (تقريبية) - باستخدام تاريخ الميلاد
        if person1.date_of_birth and person2.date_of_birth:
            today = date.today()
            
            age1 = today.year - person1.date_of_birth.year
            age2 = today.year - person2.date_of_birth.year
            
            age_diff = abs(age1 - age2)
            if age_diff <= 2:
                feature_score += 0.3
                total_weight += 0.3
            elif age_diff <= 5:
                feature_score += 0.15
                total_weight += 0.3
            elif age_diff <= 10:
                feature_score += 0.05
                total_weight += 0.3
        
        return feature_score / total_weight if total_weight > 0 else 0.5

    def match_by_name(self, report1, report2):
        """مقارنة الأسماء باستخدام التشابه النصي والصوتي"""
        if not report1.person or not report2.person:
            return 0.0
        
        name1 = str(report1.person)
        name2 = str(report2.person)
        
        if not name1 or not name2:
            return 0.0
        
        return ArabicNameMatcher.calculate_name_similarity(name1, name2)

    def calculate_hybrid_score(self, report1, report2):
        """حساب درجة المطابقة الهجينة مع تفاصيل توضيحية"""
        try:
            # حساب التشابه بالوجه
            face_sim, face_conf, face_level = self.face_matcher.calculate_similarity_batch(report1, report2)
            
            # حساب التشابه بالبيانات
            name_score = self.match_by_name(report1, report2)
            location_score = self.match_by_location(report1, report2)
            feature_score = self.match_by_features(report1, report2)
            
            # إذا كان هناك تناقض صارخ في الجنس، نضعف النتيجة
            if feature_score == 0 and report1.person and report2.person:
                if report1.person.gender and report2.person.gender and report1.person.gender != report2.person.gender:
                    return 0.0, 0.0, 'low', 'normal', {}

            # الأوزان من الإعدادات
            weights = self.config.weights
            
            hybrid_similarity = (
                (face_sim * weights['face']) +
                (name_score * weights['name']) +
                (location_score * weights['location']) +
                (feature_score * weights['features'])
            )
            
            # الثقة تعتمد بشكل أساسي على الوجه إذا وجد
            if face_conf > 0:
                hybrid_confidence = face_conf
                confidence_level = face_level
            else:
                hybrid_confidence = (name_score * 0.7 + feature_score * 0.3) * 100
                confidence_level = self.face_matcher.get_confidence_level(hybrid_confidence)
            
            # تحديد الأولوية
            priority_level = self.get_priority_level(hybrid_similarity, report1, report2)

            details = {
                'face_similarity': round(face_sim, 2),
                'name_match': round(name_score, 2),
                'location_match': round(location_score, 2),
                'feature_match': round(feature_score, 2),
                'explanation': self._generate_explanation(face_sim, name_score, location_score, feature_score)
            }
            
            return hybrid_similarity, hybrid_confidence, confidence_level, priority_level, details
            
        except Exception as e:
            logger.error(f"خطأ في حساب النتيجة الهجينة: {e}")
            return 0.0, 0.0, 'low', 'normal', {}

    def get_priority_level(self, similarity_score, report1, report2):
        """تحديد مستوى الأولوية بناءً على التشابه ونوع البلاغ"""
        # حساب العمر من تاريخ الميلاد
        age1 = self.get_age_from_person(report1.person) if report1.person else None
        age2 = self.get_age_from_person(report2.person) if report2.person else None
        
        # حالات عاجلة: أطفال أو كبار سن
        is_child = (age1 and age1 < 12) or (age2 and age2 < 12)
        is_elderly = (age1 and age1 > 60) or (age2 and age2 > 60)
        
        if is_child or is_elderly:
            if similarity_score > 0.5:
                return 'urgent'
            elif similarity_score > 0.3:
                return 'high'
        
        if similarity_score > 0.7:
            return 'high'
        elif similarity_score > 0.5:
            return 'normal'
        else:
            return 'low'
    
    def get_age_from_person(self, person):
        """حساب العمر من تاريخ الميلاد"""
        if person and person.date_of_birth:
            today = date.today()
            return today.year - person.date_of_birth.year
        return None

    def _generate_explanation(self, face, name, loc, feat):
        """توليد شرح لسبب المطابقة"""
        reasons = []
        if face > 0.8:
            reasons.append("تطابق عالي جداً في ملامح الوجه")
        elif face > 0.5:
            reasons.append("تشابه في ملامح الوجه")
        elif face > 0.3:
            reasons.append("تشابه جزئي في ملامح الوجه")
        
        if name > 0.8:
            reasons.append("تطابق في الاسم")
        elif name > 0.4:
            reasons.append("تشابه جزئي في الأسماء")
        
        if loc > 0.5:
            reasons.append("رصد في نفس المنطقة الجغرافية")
        if feat > 0.7:
            reasons.append("تشابه كبير في الصفات الجسدية")
        elif feat > 0.4:
            reasons.append("تشابه في بعض الصفات الجسدية")
        
        return " + ".join(reasons) if reasons else "تقارب في البيانات العامة"

    def run_matching_for_report(self, report):
        """تشغيل المطابقة لبلاغ محدد فوراً"""
        if report.status != 'active':
            return 0
            
        try:
            # تحديد البلاغات المقابلة
            target_type = 'found' if report.report_type == 'missing' else 'missing'
            
            # جلب البلاغات الهدف النشطة
            target_reports = Report.objects.filter(
                report_type=target_type,
                status='active'
            ).exclude(report_id=report.report_id).select_related(
                'person', 
                'lost_governorate', 'lost_district'
            )
            
            matches_count = 0
            matches_created = []
            
            for target in target_reports:
                # التحقق من عدم وجود مطابقة سابقة
                existing = self.prevent_duplicate_matches(report, target)
                if existing:
                    continue
                
                similarity, confidence, conf_level, priority, details = self.calculate_hybrid_score(report, target)
                
                if similarity >= self.config.similarity_threshold:
                    # تحديد أي بلاغ هو المفقود وأيهما المعثور عليه
                    if report.report_type == 'missing':
                        report_missing, report_found = report, target
                    else:
                        report_missing, report_found = target, report
                    
                    # حفظ النتيجة
                    match = MatchResult.objects.create(
                        report_1=report_missing,
                        report_2=report_found,
                        similarity_score=similarity,
                        confidence_level=conf_level,
                        match_type='auto',
                        match_status='pending',
                        priority_level=priority,
                        match_reason=details.get('explanation', ''),
                        match_details=details
                    )
                    
                    matches_count += 1
                    matches_created.append(match)
            
            # تسجيل عملية المطابقة
            if matches_count > 0:
                MatchingAuditLog.objects.create(
                    action_type='single_match',
                    report_count=matches_count,
                    status='success',
                    message=f"تم العثور على {matches_count} مطابقة للبلاغ {report.report_code}"
                )
                
                # إرسال إشعارات للمطابقات عالية الأولوية
                self._notify_high_priority_matches(matches_created)
            
            return matches_count
            
        except Exception as e:
            logger.error(f"خطأ في تشغيل المطابقة للبلاغ {report.report_code}: {e}")
            
            MatchingAuditLog.objects.create(
                action_type='single_match',
                status='error',
                message=str(e)
            )
            return 0
    
    def _notify_high_priority_matches(self, matches):
        """إرسال إشعارات للمطابقات عالية الأولوية"""
        try:
            from notifications.services import NotificationService
            
            for match in matches:
                if match.priority_level in ['urgent', 'high']:
                    NotificationService.notify_admins(
                        title="مطابقة جديدة عالية الأولوية",
                        message=f"تم العثور على مطابقة جديدة بنسبة {int(match.similarity_score * 100)}%",
                        link=f"/admin-dashboard/matches/{match.match_id}/"
                    )
        except ImportError:
            logger.warning("خدمة الإشعارات غير متوفرة")
        except Exception as e:
            logger.error(f"خطأ في إرسال الإشعارات: {e}")