# دليل التثبيت (Installation Guide)

يوضح هذا الملف خطوات إعداد بيئة العمل وتثبيت المكتبات اللازمة لتشغيل المشروع.

## المتطلبات المسبقة (Prerequisites)

- Python 3.8 أو أحدث.
- pip (مدير حزم بايثون).

## خطوات التثبيت (Installation Steps)

### 1. إنشاء بيئة افتراضية (Create a Virtual Environment)

من داخل مجلد المشروع، قم بتشغيل الأمر التالي لإنشاء بيئة افتراضية:

**Windows:**
```bash
python -m venv venv
```

**macOS/Linux:**
```bash
python3 -m venv venv
```

### 2. تفعيل البيئة الافتراضية (Activate the Virtual Environment)

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. تثبيت المكتبات (Install Dependencies)

بعد تفعيل البيئة، قم بتثبيت المكتبات المطلوبة باستخدام الملف `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. إعداد متغيرات البيئة (Setup Environment Variables)

قم بإنشاء ملف `.env` بجانب ملف `manage.py` وقم بإضافة المتغيرات اللازمة (مثل مفاتيح API وإعدادات قاعدة البيانات). يمكنك استخدام ملف `.env.example` كنموذج (إذا كان موجوداً).

### 5. ترحيل قاعدة البيانات (Migrate Database)

```bash
python manage.py migrate
```

### 6. ملفات النماذج (Model Weights)

ملفات النماذج الكبيرة (مثل `.h5`) غير مرفوعة على GitHub. يجب عليك وضعها يدوياً في المسارات التالية:
- `models/feature_extractor.h5`
- `matching/ml_models/best_siamese.weights.h5`

### 7. تشغيل الخادم (Run Server)

```bash
python manage.py runserver
```

الآن يمكنك الوصول للمشروع عبر المتصفح على الرابط: `http://127.0.0.1:8000/`
