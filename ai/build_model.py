import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Dropout, Lambda, GlobalAveragePooling2D, BatchNormalization
from tensorflow.keras.applications import MobileNetV2
import tensorflow.keras.backend as K

def cosine_distance(vectors):
    """
    حساب تشابه جيب التمام (Cosine Similarity)
    """
    (featsA, featsB) = vectors
    # جمع القيم (Dot Product) للمتجهات المطبعة
    return K.sum(featsA * featsB, axis=1, keepdims=True)

def build_siamese_model(input_shape):
    print("[INFO] Building Model (MobileNetV2 Frozen + Sigmoid Head)...")
    
    # 1. القاعدة: MobileNetV2
    base_cnn = MobileNetV2(weights="imagenet", include_top=False, input_shape=input_shape)
    
    # --- استراتيجية التجميد (حماية النموذج من النسيان) ---
    # نجمد كل شيء ما عدا آخر 30 طبقة (تعديل طفيف للأوزان)
    for layer in base_cnn.layers[:-50]:
        layer.trainable = False
    for layer in base_cnn.layers[-50:]:
        layer.trainable = True

    # 2. الرأس (Head)
    x = base_cnn.output
    x = GlobalAveragePooling2D()(x)
    x = BatchNormalization()(x) # إضافة استقرار
    x = Dense(256, activation="relu")(x)
    x = Dropout(0.2)(x) # إبقاء الـ Dropout
    
    # تطبيع المتجهات (ضروري جداً للـ Cosine)
    x = Lambda(lambda v: K.l2_normalize(v, axis=1))(x)

    embedding_network = Model(base_cnn.input, x, name="Embedding_Network")

    # 3. الشبكة التوأمية
    imgA = Input(shape=input_shape)
    imgB = Input(shape=input_shape)

    featsA = embedding_network(imgA)
    featsB = embedding_network(imgB)

    # حساب المسافة (Cosine)
    distance = Lambda(cosine_distance)([featsA, featsB])
    
    # طبقة القرار (Sigmoid): تخرج رقم بين 0 و 1
    outputs = Dense(1, activation="sigmoid")(distance)

    model = Model(inputs=[imgA, imgB], outputs=outputs)
    
    return model, embedding_network
