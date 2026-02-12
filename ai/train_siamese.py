import tensorflow as tf
from tensorflow.keras.callbacks import ModelCheckpoint, ReduceLROnPlateau, EarlyStopping
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import os
import numpy as np
import config
from create_pairs import create_pairs
from build_model import build_siamese_model
import glob
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------
# 1. Pipeline Functions
# ---------------------------------------------------------
def read_image(file_path):
    img = tf.io.read_file(file_path)
    img = tf.image.decode_jpeg(img, channels=3)
    img = tf.image.resize(img, (224, 224))
    img = preprocess_input(img)
    return img

def augment_image(img):
    img = tf.image.random_flip_left_right(img)
    img = tf.image.random_brightness(img, max_delta=0.1)
    return img

def process_pair_train(path_a, path_b, label):
    imgA = read_image(path_a)
    imgB = read_image(path_b)
    imgA = augment_image(imgA)
    imgB = augment_image(imgB)
    return (imgA, imgB), label

def process_pair_val(path_a, path_b, label):
    imgA = read_image(path_a)
    imgB = read_image(path_b)
    return (imgA, imgB), label

# ---------------------------------------------------------
# 2. Training Loop
# ---------------------------------------------------------
def train():
    for directory in [config.CHECKPOINT_DIR, config.MODELS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    # هذا السطر هو الأهم: سيستخدم create_pairs الجديد (Random pairs)
    print("[INFO] Loading pairs (Robust Generation)...")
    pairs, labels = create_pairs(config.TRAIN_DIR)
    
    if len(pairs) == 0: return

    train_pairs, val_pairs, train_labels, val_labels = train_test_split(
        pairs, labels, test_size=0.2, random_state=42, shuffle=True
    )

    def build_dataset(p, l, is_training=True):
        dataset = tf.data.Dataset.from_tensor_slices((p[:, 0], p[:, 1], l))
        if is_training:
            dataset = dataset.shuffle(buffer_size=2048)
            process_func = process_pair_train
        else:
            process_func = process_pair_val
        dataset = dataset.map(process_func, num_parallel_calls=tf.data.AUTOTUNE)
        dataset = dataset.batch(config.BATCH_SIZE)
        dataset = dataset.prefetch(buffer_size=tf.data.AUTOTUNE)
        return dataset

    train_dataset = build_dataset(train_pairs, train_labels, is_training=True)
    val_dataset = build_dataset(val_pairs, val_labels, is_training=False)

    print("[INFO] Building Model (Sigmoid / Binary Crossentropy)...")
    model, embedding_model = build_siamese_model(config.INPUT_SHAPE)
    
    # العودة لـ Binary Crossentropy المتوافقة مع Sigmoid
    optimizer = Adam(learning_rate=0.0001) # معدل تعلم هادئ
    model.compile(loss="binary_crossentropy", optimizer=optimizer, metrics=["accuracy"])

    checkpoint_filename = "best_siamese.weights.h5"
    checkpoint_path = os.path.join(config.CHECKPOINT_DIR, checkpoint_filename)

    if os.path.exists(checkpoint_path):
        print(f"[INFO] Loading best weights from: {checkpoint_path}")
        model.load_weights(checkpoint_path)
    else:
        print("[INFO] Starting fresh training.")

    callbacks = [
        ModelCheckpoint(
            filepath=checkpoint_path,
            save_weights_only=True,
            monitor='val_loss',
            mode='min',
            save_best_only=True,
            verbose=1
        ),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1),
        EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True, verbose=1)
    ]

    print("[INFO] Starting Training Loop...")
    model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=config.EPOCHS,
        callbacks=callbacks
    )

    print("\n[INFO] Saving Final Feature Extractor Model...")
    embedding_model.save(config.MODEL_PATH)
    print("Training Complete.")

if __name__ == "__main__":
    train()
