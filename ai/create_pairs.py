import os
import numpy as np
import random
import config

def create_pairs(dataset_dir):
    print(f"[INFO] Creating Robust Pairs from: {dataset_dir}")
    
    person_images_map = {}
    if not os.path.exists(dataset_dir):
        print(f"[ERROR] Directory not found: {dataset_dir}")
        return np.array([]), np.array([])

    all_people = os.listdir(dataset_dir)
    # تصفية المجلدات الفارغة أو الملفات غير المجلدات
    all_people = [p for p in all_people if os.path.isdir(os.path.join(dataset_dir, p))]
    
    print(f"[INFO] Found {len(all_people)} classes (people).")

    # 1. تحميل كل الصور في الذاكرة (كـ مسارات)
    for person_name in all_people:
        person_dir = os.path.join(dataset_dir, person_name)
        images = []
        for img_name in os.listdir(person_dir):
            if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                images.append(os.path.join(person_dir, img_name))
        
        # نحتاج صورتين على الأقل لتكوين زوج موجب
        if len(images) > 1:
            person_images_map[person_name] = images

    valid_people = list(person_images_map.keys())
    pairs = []
    labels = []

    print("[INFO] Generating Random Hard Pairs...")
    
    for person_name, person_imgs in person_images_map.items():
        # نمر على كل صورة للشخص
        for i, current_img in enumerate(person_imgs):
            
            # -------------------------------------------------
            # 1. الزوج الموجب (Positive Pair) - العشوائي القوي
            # -------------------------------------------------
            # بدلاً من أخذ الصورة التالية (i+1)، نأخذ أي صورة أخرى عشوائية لنفس الشخص
            # هذا يمنع النموذج من حفظ "تسلسل الفيديو" أو "الإضاءة المتشابهة"
            
            possible_indices = [k for k in range(len(person_imgs)) if k != i]
            if not possible_indices: continue # حماية إضافية
            
            random_pos_idx = random.choice(possible_indices)
            pos_img = person_imgs[random_pos_idx]
            
            pairs.append([current_img, pos_img])
            labels.append(1.0) # 1 = متشابهين

            # -------------------------------------------------
            # 2. الزوج السالب (Negative Pair)
            # -------------------------------------------------
            # نختار شخصاً آخر عشوائياً
            random_person = random.choice(valid_people)
            while random_person == person_name and len(valid_people) > 1:
                random_person = random.choice(valid_people)
            
            if random_person != person_name:
                neg_img = random.choice(person_images_map[random_person])
                pairs.append([current_img, neg_img])
                labels.append(0.0) # 0 = مختلفين

    # تحويل القوائم إلى Numpy Arrays
    pairs = np.array(pairs)
    labels = np.array(labels).astype('float32')
    
    # خلط البيانات جيداً (Shuffle) لكسر أي ترتيب زمني
    indices = np.arange(len(pairs))
    np.random.shuffle(indices)
    pairs = pairs[indices]
    labels = labels[indices]

    print(f"[STATS] Total Generated Pairs: {len(pairs)}")
    print(f" -> Positives: {np.sum(labels == 1.0)}")
    print(f" -> Negatives: {np.sum(labels == 0.0)}")
    
    return pairs, labels

if __name__ == "__main__":
    # للاختبار السريع
    create_pairs(config.TRAIN_DIR)
