import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATASET_DIR = os.path.join(BASE_DIR, "dataset", "raw")
PROCESSED_DATASET_DIR = os.path.join(BASE_DIR, "dataset", "processed")
TRAIN_DIR = os.path.join(PROCESSED_DATASET_DIR, "train")
TEST_DIR = os.path.join(PROCESSED_DATASET_DIR, "test")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "feature_extractor.h5")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "checkpoints") 

INPUT_SHAPE = (224, 224, 3) # شكل المدخلات
BATCH_SIZE = 32  # تقليل الدفعة قليلاً لأننا فككنا تجميد النموذج (ليتسع في الذاكرة)
LEARNING_RATE = 0.0005 # رفعنا المعدل (كان 0.0001)
EPOCHS = 60

for directory in [MODELS_DIR, CHECKPOINT_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
