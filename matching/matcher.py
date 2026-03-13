import json
import numpy as np
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, date
import logging
import re
import jellyfish

from reports.models import Report, ReportImage
from .models import MatchResult

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


class FaceMatcher:
    """مطابقة الوجوه باستخدام الذكاء الاصطناعي"""
    
    def __init__(self):
        self.config = MatchingConfig()
    
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
    
    def get_age_from_person(self, person):
        """حساب العمر من تاريخ الميلاد"""
        if person and person.date_of_birth:
            today = date.today()
            return today.year - person.date_of_birth.year
        return None
    
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
    
    def match_single_pair(self, report1, report2):
        """مطابقة زوج واحد باستخدام الصور"""
        try:
            # الحصول على الصور مع البصمات
            report1_images = ReportImage.objects.filter(
                report=report1,
                face_embedding__isnull=False
            )
            report2_images = ReportImage.objects.filter(
                report=report2,
                face_embedding__isnull=False
            )
            
            if not report1_images.exists() or not report2_images.exists():
                return 0.0, 0.0, 'low'
            
            best_similarity = 0.0
            best_quality1 = 0.0
            best_quality2 = 0.0
            
            # المقارنة بين جميع الصور
            for img1 in report1_images:
                for img2 in report2_images:
                    sim = self.calculate_similarity(img1.face_embedding, img2.face_embedding)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_quality1 = img1.quality_score or 0.5
                        best_quality2 = img2.quality_score or 0.5
            
            if best_similarity > 0:
                confidence = self.calculate_confidence(best_similarity, best_quality1, best_quality2)
                confidence_level = self.get_confidence_level(confidence)
                return best_similarity, confidence, confidence_level
            
            return 0.0, 0.0, 'low'
            
        except Exception as e:
            logger.error(f"خطأ في مطابقة الزوج: {e}")
            return 0.0, 0.0, 'low'


class ReportMatcher:
    """محرك المطابقة الهجين (وجه + بيانات)"""
    
    def __init__(self):
        self.face_matcher = FaceMatcher()
        self.config = self.face_matcher.config

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
            
            # حساب العمر التقريبي لكل شخص
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
    
    def normalize_arabic(self, text):
        """توحيد الحروف العربية المتشابهة لتسهيل المطابقة"""
        if not text:
            return ""
        # توحيد الألفات
        text = re.sub("[إأآا]", "ا", text)
        # توحيد الهاء والتاء المربوطة
        text = re.sub("ة", "ه", text)
        # توحيد الياء والألف المقصورة
        text = re.sub("ى", "ي", text)
        # إزالة العلامات (التشكيل)
        text = re.sub(r'[\u064B-\u0652]', '', text)
        return text.strip()

    def match_by_name(self, report1, report2):
        """مقارنة الأسماء باستخدام التشابه النصي والصوتي"""
        if not report1.person or not report2.person:
            return 0.0
        
        name1 = self.normalize_arabic(str(report1.person))
        name2 = self.normalize_arabic(str(report2.person))
        
        if not name1 or not name2:
            return 0.0
        
        # تطابق تام بعد التوحيد
        if name1 == name2:
            return 1.0
            
        # استخدام خوارزمية Jaro-Winkler للأسماء
        jaro_sim = jellyfish.jaro_winkler_similarity(name1, name2)
        
        # استخدام Levenshtein للكلمات المشتركة
        words1 = name1.split()
        words2 = name2.split()
        
        match_count = 0
        for w1 in words1:
            for w2 in words2:
                if jellyfish.levenshtein_distance(w1, w2) <= 1:
                    match_count += 1
                    break
        
        word_sim = (2 * match_count) / (len(words1) + len(words2)) if (len(words1) + len(words2)) > 0 else 0.0
        
        # النتيجة النهائية هي مزيج بينهما
        final_score = (jaro_sim * 0.4) + (word_sim * 0.6)
        
        return final_score

    def calculate_hybrid_score(self, report1, report2):
        """حساب درجة المطابقة الهجينة مع تفاصيل توضيحية"""
        try:
            # حساب التشابه بالوجه
            face_sim, face_conf, face_level = self.face_matcher.match_single_pair(report1, report2)
            
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
            priority_level = self.face_matcher.get_priority_level(hybrid_similarity, report1, report2)

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
                'lost_governorate', 'lost_district', 'lost_uzlah'
            )
            
            matches_count = 0
            for target in target_reports:
                similarity, confidence, conf_level, priority, details = self.calculate_hybrid_score(report, target)
                
                if similarity >= self.config.similarity_threshold:
                    # تحديد أي بلاغ هو المفقود وأيهما المعثور عليه
                    if report.report_type == 'missing':
                        report_missing, report_found = report, target
                    else:
                        report_missing, report_found = target, report
                    
                    # حفظ النتيجة
                    match, created = MatchResult.objects.get_or_create(
                        report_1=report_missing,
                        report_2=report_found,
                        defaults={
                            'similarity_score': similarity,
                            'confidence_level': conf_level,
                            'match_type': 'auto',
                            'match_status': 'pending',
                            'priority_level': priority,
                            'match_reason': details.get('explanation', ''),
                            'match_details': details
                        }
                    )
                    
                    if not created:
                        # تحديث النتيجة إذا كانت أفضل
                        if similarity > match.similarity_score:
                            match.similarity_score = similarity
                            match.confidence_level = conf_level
                            match.priority_level = priority
                            match.match_details = details
                            match.save(update_fields=['similarity_score', 'confidence_level', 'priority_level', 'match_details'])
                    
                    matches_count += 1
            
            # تسجيل عملية المطابقة
            if matches_count > 0:
                from .models import MatchingAuditLog
                MatchingAuditLog.objects.create(
                    action_type='single_match',
                    report_count=matches_count,
                    status='success',
                    message=f"تم العثور على {matches_count} مطابقة للبلاغ {report.report_code}"
                )
            
            return matches_count
            
        except Exception as e:
            logger.error(f"خطأ في تشغيل المطابقة للبلاغ {report.report_code}: {e}")
            
            # تسجيل الخطأ
            from .models import MatchingAuditLog
            MatchingAuditLog.objects.create(
                action_type='single_match',
                status='error',
                message=str(e)
            )
            return 0