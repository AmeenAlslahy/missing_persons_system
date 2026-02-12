import os
import numpy as np
import tensorflow as tf
import cv2
import matplotlib.pyplot as plt
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import random
import config
from build_model import build_siamese_model

# ---------------------------------------------------------
# 1. High-Resolution Saliency Map (الخريطة الدقيقة)
# ---------------------------------------------------------
def make_high_res_heatmap(img_tensor, embedding_network, reference_tensor):
    """
    توليد خريطة حرارية دقيقة بناءً على تدرجات الصورة المباشرة
    """
    try:
        with tf.GradientTape() as tape:
            tape.watch(img_tensor)
            
            # حساب البصمة
            embedding = embedding_network(img_tensor)
            ref_embedding = embedding_network(reference_tensor)
            
            # الهدف: تعظيم التشابه
            similarity = tf.reduce_sum(embedding * ref_embedding)
            
        # حساب التدرج بالنسبة للصورة الأصلية
        grads = tape.gradient(similarity, img_tensor)
        
        if grads is None: return np.zeros((224, 224))
            
        # تحويل التدرجات لخريطة حرارية
        heatmap = tf.reduce_max(tf.abs(grads), axis=-1)[0]
        heatmap = tf.maximum(heatmap, 0)
        
        # تطبيع
        max_val = tf.math.reduce_max(heatmap)
        if max_val > 0:
            heatmap = heatmap / max_val
            
        # تنعيم خفيف
        heatmap_np = heatmap.numpy()
        heatmap_np = cv2.GaussianBlur(heatmap_np, (3, 3), 0)
        
        return heatmap_np

    except Exception as e:
        print(f"[ERROR] Heatmap generation failed: {e}")
        return np.zeros((224, 224))

# ---------------------------------------------------------
# 2. دوال العرض والمعالجة
# ---------------------------------------------------------
def overlay_heatmap_smart(img_path, heatmap):
    """دمج ذكي يبرز المناطق المهمة"""
    img = cv2.imread(img_path)
    if img is None: return np.zeros((224, 224, 3))
    img = cv2.resize(img, (224, 224))
    
    heatmap_uint8 = np.uint8(255 * heatmap)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    
    mask = heatmap[..., np.newaxis]
    alpha = 0.6
    output = (1 - mask * alpha) * img + (mask * alpha) * heatmap_color
    output = np.clip(output, 0, 255).astype(np.uint8)
    
    return cv2.cvtColor(output, cv2.COLOR_BGR2RGB)

def prepare_image(img_path):
    try:
        if not os.path.exists(img_path): return None
        img = image.load_img(img_path, target_size=config.INPUT_SHAPE[:2])
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)
        return tf.convert_to_tensor(img_array, dtype=tf.float32)
    except: return None

# ---------------------------------------------------------
# 3. التحليل الرئيسي
# ---------------------------------------------------------
def analyze_similarity(person_name="ameen"):
    THRESHOLD = 0.65 
    
    print("=" * 60)
    print(f"🔍 Deep Pixel-Wise Analysis - Person: {person_name}")
    print("=" * 60)
    
    test_dir = config.TEST_DIR
    person_dir = os.path.join(test_dir, person_name)
    
    if not os.path.exists(person_dir):
        print(f"[ERROR] Directory not found: {person_dir}")
        return

    images = [os.path.join(person_dir, f) for f in os.listdir(person_dir) 
              if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    
    if len(images) < 2:
        print("[ERROR] Need at least 2 images.")
        return
        
    # اختيار عشوائي
    selected_images = random.sample(images, 2)
    img1_path = selected_images[0]
    img2_path = selected_images[1]
    
    print(f"[INFO] Analyzing:\n 1. {os.path.basename(img1_path)}\n 2. {os.path.basename(img2_path)}")

    # تحميل النموذج
    model, embedding_network = build_siamese_model(config.INPUT_SHAPE)
    if os.path.exists(config.MODEL_PATH):
        try:
            embedding_network.load_weights(config.MODEL_PATH)
        except: pass
    else:
        print("[ERROR] Model weights not found.")
        return

    # التجهيز والحساب
    img1_tensor = prepare_image(img1_path)
    img2_tensor = prepare_image(img2_path)
    if img1_tensor is None or img2_tensor is None: return

    emb1 = embedding_network.predict(img1_tensor, verbose=0)
    emb2 = embedding_network.predict(img2_tensor, verbose=0)
    similarity = np.dot(emb1, emb2.T)[0][0]
    
    percentage = similarity * 100
    is_same_person = similarity > THRESHOLD
    
    status_text = "MATCH (Same Person) ✅" if is_same_person else "MISMATCH (Different) ❌"
    color_code = 'green' if is_same_person else 'red'

    print(f"\n[RESULT] Score: {similarity:.4f} ({percentage:.2f}%)")
    print(f"[DECISION] {status_text}")

    # توليد الخرائط
    print("[INFO] Generating High-Res Heatmaps...")
    heatmap1 = make_high_res_heatmap(img1_tensor, embedding_network, img2_tensor)
    heatmap2 = make_high_res_heatmap(img2_tensor, embedding_network, img1_tensor)

    # العرض
    final_img1 = overlay_heatmap_smart(img1_path, heatmap1)
    final_img2 = overlay_heatmap_smart(img2_path, heatmap2)

    plt.figure(figsize=(14, 7))
    
    ax1 = plt.subplot(1, 2, 1)
    plt.imshow(final_img1)
    plt.title(f"Focus Points (Image 1)", fontsize=12)
    plt.axis('off')
    
    ax2 = plt.subplot(1, 2, 2)
    plt.imshow(final_img2)
    plt.title(f"Focus Points (Image 2)", fontsize=12)
    plt.axis('off')
    
    plt.suptitle(f"Similarity: {percentage:.2f}%\n{status_text}", 
                 fontsize=18, color=color_code, weight='bold', y=0.95)
    
    plt.tight_layout()
    
    output_path = "detailed_analysis_result.png"
    plt.savefig(output_path, dpi=150)
    print(f"\n✅ [SUCCESS] Saved to {output_path}")
    
    plt.show()

if __name__ == "__main__":
    analyze_similarity()
