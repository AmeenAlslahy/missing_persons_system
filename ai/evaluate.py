import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns
import cv2
from sklearn.metrics import accuracy_score, roc_curve, auc, confusion_matrix
import random
import config
from build_model import build_siamese_model

# ---------------------------------------------------------
# 1. دوال تجهيز البيانات
# ---------------------------------------------------------

def read_image_eval(file_path):
    img = tf.io.read_file(file_path)
    img = tf.image.decode_jpeg(img, channels=3)
    img = tf.image.resize(img, (224, 224))
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
    img = preprocess_input(img)
    return img

def create_test_pairs(test_dir, max_pairs=3000):
    print(f"[INFO] Scanning Test Directory: {test_dir}")
    person_to_images = {}
    if not os.path.exists(test_dir):
        print(f"[ERROR] Test directory not found.")
        return [], []

    for person_name in os.listdir(test_dir):
        person_dir = os.path.join(test_dir, person_name)
        if not os.path.isdir(person_dir): continue
        images = [os.path.join(person_dir, f) for f in os.listdir(person_dir) 
                  if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        if len(images) > 0:
            person_to_images[person_name] = images

    people_names = list(person_to_images.keys())
    if len(people_names) < 2:
        return [], []

    pairs = []
    labels = []
    
    print("[INFO] Generating test pairs...")
    
    # Positive Pairs
    for person in people_names:
        imgs = person_to_images[person]
        if len(imgs) < 2: continue
        import itertools
        possible = list(itertools.combinations(imgs, 2))
        if len(possible) > 50: possible = random.sample(possible, 50)
        for p in possible:
            pairs.append(p)
            labels.append(1.0)

    # Negative Pairs
    num_neg = len(pairs)
    for _ in range(num_neg):
        p1, p2 = random.sample(people_names, 2)
        while p1 == p2: p1, p2 = random.sample(people_names, 2)
        img1 = random.choice(person_to_images[p1])
        img2 = random.choice(person_to_images[p2])
        pairs.append([img1, img2])
        labels.append(0.0)

    pairs = np.array(pairs)
    labels = np.array(labels)
    
    indices = np.arange(len(pairs))
    np.random.shuffle(indices)
    pairs = pairs[indices]
    labels = labels[indices]
    
    if len(pairs) > max_pairs:
        pairs = pairs[:max_pairs]
        labels = labels[:max_pairs]
        
    print(f"[STATS] Test Pairs: {len(pairs)} (Pos: {np.sum(labels==1)}, Neg: {np.sum(labels==0)})")
    return pairs, labels

# ---------------------------------------------------------
# 2. دوال الرسم والحفظ
# ---------------------------------------------------------

def save_visual_report(pairs, labels, predictions, threshold):
    pred_labels = (predictions.flatten() > threshold).astype(float)
    
    # تصنيف الحالات
    tp_idx = np.where((pred_labels == 1) & (labels == 1))[0] # صحيح - متشابه
    tn_idx = np.where((pred_labels == 0) & (labels == 0))[0] # صحيح - مختلف
    fp_idx = np.where((pred_labels == 1) & (labels == 0))[0] # خطأ - توقع تشابه
    fn_idx = np.where((pred_labels == 0) & (labels == 1))[0] # خطأ - لم يعرفه

    print("\n" + "="*40)
    print("📊 VISUAL INSPECTION STATS")
    print("="*40)
    print(f"✅ True Positives: {len(tp_idx)}")
    print(f"✅ True Negatives: {len(tn_idx)}")
    print(f"❌ False Positives: {len(fp_idx)}")
    print(f"❌ False Negatives: {len(fn_idx)}")

    # دالة لرسم وحفظ العينات
    def save_plot_grid(indices, title, filename, color):
        if len(indices) == 0: return
        samples = np.random.choice(indices, min(len(indices), 5), replace=False)
        
        plt.figure(figsize=(15, 4))
        plt.suptitle(f"{title} (Threshold: {threshold:.2f})", fontsize=14, color=color, weight='bold')
        
        for i, idx in enumerate(samples):
            imgA = cv2.imread(pairs[idx][0])
            imgB = cv2.imread(pairs[idx][1])
            if imgA is None or imgB is None: continue
            
            imgA = cv2.cvtColor(imgA, cv2.COLOR_BGR2RGB)
            imgB = cv2.cvtColor(imgB, cv2.COLOR_BGR2RGB)
            imgA = cv2.resize(imgA, (160, 160))
            imgB = cv2.resize(imgB, (160, 160))
            
            # وضع خط فاصل ملون
            border = np.ones((160, 10, 3), dtype=np.uint8) * 255
            concat_img = np.hstack((imgA, border, imgB))
            
            ax = plt.subplot(1, 5, i + 1)
            plt.imshow(concat_img)
            score = predictions[idx][0]
            plt.title(f"Score: {score:.3f}", fontsize=10)
            plt.axis("off")
        
        plt.tight_layout()
        plt.savefig(filename)
        print(f"💾 Saved: {filename}")
        plt.close()

    # حفظ الصور
    save_plot_grid(tp_idx, "CORRECT MATCHES (Same Person)", "report_correct_match.png", "green")
    save_plot_grid(tn_idx, "CORRECT REJECTIONS (Diff People)", "report_correct_reject.png", "blue")
    save_plot_grid(fp_idx, "FALSE POSITIVES (Wrong Match)", "report_error_false_match.png", "red")
    save_plot_grid(fn_idx, "FALSE NEGATIVES (Missed Match)", "report_error_missed.png", "orange")

def run_evaluation():
    print("\n1️⃣ Loading Model...")
    model, _ = build_siamese_model(config.INPUT_SHAPE)
    
    # تحميل الأوزان
    if os.path.exists(config.MODEL_PATH):
        # نحاول تحميل النموذج النهائي أولاً
        try:
            print(f"[INFO] Loading from: {config.MODEL_PATH}")
            model.load_weights(config.MODEL_PATH) # هنا قد نحتاج load_weights للنموذج الكامل
            # إذا فشل لأن MODEL_PATH هو embedding فقط، نلجأ لل checkpoint
        except:
             pass
             
    # الأفضل دائماً استخدام الـ Checkpoint للتقييم
    import glob
    checkpoints = glob.glob(os.path.join(config.CHECKPOINT_DIR, "*.weights.h5"))
    if checkpoints:
        latest = max(checkpoints, key=os.path.getctime)
        print(f"[INFO] Loading weights from Best Checkpoint: {latest}")
        model.load_weights(latest)
    
    # تجهيز البيانات
    pairs, labels = create_test_pairs(config.TEST_DIR)
    if len(pairs) == 0: return

    def _parse(p1, p2):
        return (read_image_eval(p1), read_image_eval(p2)), 0.0

    test_ds = tf.data.Dataset.from_tensor_slices((pairs[:, 0], pairs[:, 1]))
    test_ds = test_ds.map(_parse, num_parallel_calls=tf.data.AUTOTUNE)
    test_ds = test_ds.batch(config.BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    print("\n2️⃣ Running Predictions...")
    predictions = model.predict(test_ds, verbose=1)
    
    y_true = labels
    y_scores = predictions.flatten()
    
    # حساب أفضل Threshold
    thresholds = np.arange(0.01, 0.99, 0.01)
    best_acc = 0
    best_thresh = 0.5
    
    for t in thresholds:
        acc = accuracy_score(y_true, (y_scores > t).astype(int))
        if acc > best_acc:
            best_acc = acc
            best_thresh = t

    print("\n" + "="*40)
    print(f"🏆 FINAL REPORT")
    print("="*40)
    print(f"Best Accuracy:     {best_acc*100:.2f}%")
    print(f"Optimal Threshold: {best_thresh:.2f}")

    # حفظ التقارير الصورية
    save_visual_report(pairs, y_true, predictions, threshold=best_thresh)
    
    # رسم وحفظ ROC Curve
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    
    plt.figure(figsize=(10, 5))
    
    plt.subplot(1, 2, 1)
    sns.histplot(y_scores[y_true==1], color='green', label='Same', kde=True, alpha=0.5)
    sns.histplot(y_scores[y_true==0], color='red', label='Different', kde=True, alpha=0.5)
    plt.axvline(best_thresh, color='black', linestyle='--')
    plt.legend()
    plt.title("Score Distribution")

    plt.subplot(1, 2, 2)
    plt.plot(fpr, tpr, color='blue', label=f'AUC = {roc_auc:.2f}')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.title("ROC Curve")
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("report_roc_curve.png")
    print("💾 Saved: report_roc_curve.png")

if __name__ == "__main__":
    run_evaluation()
