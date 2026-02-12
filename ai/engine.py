import numpy as np
import cv2
import os
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing import image
import mediapipe as mp
import mediapipe as mp
# import config # Conflict with django config
from ai import config as ai_config
from ai.build_model import build_siamese_model # ضروري لبناء الهيكل

# ==========================================
# 1. إعدادات النظام
# ==========================================
THRESHOLD = 0.32  # العتبة التي حددناها (قابلة للتعديل)

print("[AI ENGINE] Initializing...")

# إعداد كاشف الوجوه مرة واحدة (للسرعة)
# إعداد كاشف الوجوه مرة واحدة (للسرعة)
# إعداد كاشف الوجوه مرة واحدة (للسرعة)
mp_face_detection = None
face_detector = None
try:
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
        mp_face_detection = mp.solutions.face_detection
    else:
        # Try import
        try:
             from mediapipe import solutions
             mp_face_detection = solutions.face_detection
        except (ImportError, AttributeError):
             pass

    if mp_face_detection:
        face_detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
    else:
        print("[WARNING] MediaPipe FaceDetection not available. AI features will be disabled.")

except Exception as e:
    print(f"[ERROR] Failed to initialize MediaPipe: {e}")


feature_model = None

# ==========================================
# 2. تحميل النموذج (بناء الهيكل + صب الأوزان)
# ==========================================
def load_feature_model():
    global feature_model
    if feature_model is not None: return True # تم التحميل مسبقاً

    print(f"[AI ENGINE] Loading Model Logic...")
    
    # 1. بناء الهيكل الفارغ
    try:
        _, embedding_layer = build_siamese_model(ai_config.INPUT_SHAPE)
    except Exception as e:
        print(f"[ERROR] Could not build model architecture: {e}")
        return False

    # 2. البحث عن ملف الأوزان
    weights_path = ai_config.MODEL_PATH
    
    # خطة بديلة: إذا لم نجد الملف النهائي، نبحث في الـ checkpoints
    if not os.path.exists(weights_path):
        import glob
        checkpoints = glob.glob(os.path.join(ai_config.CHECKPOINT_DIR, "*.weights.h5"))
        if checkpoints:
            weights_path = max(checkpoints, key=os.path.getctime)
            print(f"[INFO] Using latest checkpoint: {weights_path}")
        else:
            print("[ERROR] No model weights found!")
            return False

    # 3. تحميل الأوزان
    try:
        # ملاحظة: إذا كانت الأوزان محفوظة لنموذج Siamese كامل، قد نحتاج تحميلها للكامل ثم استخلاص الـ embedding
        # لكن الكود الحالي مصمم ليحمل بمرونة
        embedding_layer.load_weights(weights_path, by_name=True, skip_mismatch=True)
        feature_model = embedding_layer
        print("✅ [AI ENGINE] Model loaded successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to load weights: {e}")
        # محاولة أخيرة: تحميل كنموذج كامل
        try:
            full_model, _ = build_siamese_model(ai_config.INPUT_SHAPE)
            full_model.load_weights(weights_path)
            feature_model = full_model.get_layer("Embedding_Network")
            print("✅ [AI ENGINE] Recovered via full model load.")
            return True
        except:
            return False

# تحميل أولي
load_feature_model()

class FaceEngine:
    
    @staticmethod
    def extract_face(img_path):
        """
        تقوم بقراءة الصورة واكتشاف الوجه وقصه
        """
        if not os.path.exists(img_path): return None
        
        # قراءة الصورة
        img = cv2.imread(img_path)
        if img is None: return None
        
        # تحويل لـ RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        if face_detector is None:
            # Fallback or return full image if detection disabled
            return img_rgb
            
        # كشف الوجه
        results = face_detector.process(img_rgb)
        
        if results.detections:
            h, w, c = img.shape
            # أخذ أكبر وجه
            largest_face = max(results.detections, key=lambda d: d.location_data.relative_bounding_box.width * d.location_data.relative_bounding_box.height)
            bbox = largest_face.location_data.relative_bounding_box
            
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            fw = int(bbox.width * w)
            fh = int(bbox.height * h)
            
            # Padding
            pad_w = int(fw * 0.2)
            pad_h = int(fh * 0.2)
            
            x1 = max(0, x - pad_w)
            y1 = max(0, y - pad_h)
            x2 = min(w, x + fw + pad_w)
            y2 = min(h, y + fh + pad_h)
            
            face = img_rgb[y1:y2, x1:x2]
            
            # حماية من القص الخاطئ (أبعاد صفرية)
            if face.size == 0: return img_rgb
            return face
        else:
            # لم يتم العثور على وجه، نرجع الصورة كاملة
            return img_rgb

    @staticmethod
    def preprocess_face(face_img):
        """تجهيز الوجه للنموذج"""
        if face_img is None: return None
        
        # تغيير الحجم
        face_resized = cv2.resize(face_img, (224, 224))
        
        # تحويل لمصفوفة
        img_array = image.img_to_array(face_resized)
        img_array = np.expand_dims(img_array, axis=0)
        
        # تطبيع (MobileNet Style)
        img_array = preprocess_input(img_array)
        return img_array

    @staticmethod
    def get_embedding(img_path):
        """
        الدالة الرئيسية التي يستدعيها السيرفر
        1. تقص الوجه
        2. تستخرج البصمة
        """
        if feature_model is None:
            if not load_feature_model(): return None

        # 1. استخراج الوجه
        face_img = FaceEngine.extract_face(img_path)
        if face_img is None: return None
        
        # 2. المعالجة
        processed_img = FaceEngine.preprocess_face(face_img)
        
        # 3. التوقع
        vector = feature_model.predict(processed_img, verbose=0)
        return vector[0]

    @staticmethod
    def check_similarity(img_path1, img_path2):
        """
        دالة مساعدة للمقارنة المباشرة بين ملفين
        """
        vec1 = FaceEngine.get_embedding(img_path1)
        vec2 = FaceEngine.get_embedding(img_path2)
        
        if vec1 is None or vec2 is None:
            return False, 0.0
            
        # Cosine Similarity
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        score = np.dot(vec1, vec2) / (norm1 * norm2)
        
        is_match = score > THRESHOLD
        return is_match, score
