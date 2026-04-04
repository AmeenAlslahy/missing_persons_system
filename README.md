# 📚 نظام البحث عن المفقودين (Missing Persons System) - Backend API

نظام متقدم يعتمد على الذكاء الاصطناعي (AI) والتعرف على الوجوه لربط البلاغات عن المفقودين ببعضها البعض وتسهيل عملية العثور عليهم. يوفر هذا المشروع الواجهة البرمجية (API) القوية التي تدعم تطبيقات الهاتف والمواقع الإلكترونية.

---

## 🛠️ تعليمات التنصيب (Installation Guide)

اتبع الخطوات التالية لتشغيل المشروع على جهازك المحلي:

### 1. المتطلبات الأساسية
*   Python 3.10 أو أحدث.
*   قاعدة بيانات SQL Server أو PostgreSQL (المشروع مهيأ افتراضياً لـ SQL Server).

### 2. تحميل المشروع وبيئة العمل
```bash
# استنساخ المستودع
git clone https://github.com/AmeenAlslahy/missing_persons_system.git
cd missing_persons_system

# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة (Windows)
venv\Scripts\activate
```

### 3. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 4. إعداد الملفات البيئية (.env)
قم بإنشاء ملف باسم `.env` في المجلد الرئيسي وأضف الإعدادات التالية:
```env
DEBUG=True
SECRET_KEY=your_secret_key_here
DB_NAME=missing_persons_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=1433
```

### 5. تهيئة قاعدة البيانات
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser  # لإنشاء حساب مدير
```

### 6. التشغيل
```bash
python manage.py runserver
```

---

## 📱 الربط مع تطبيق الأندرويد (Android Integration)

عند العمل على تطبيق أندرويد باستخدام (Retrofit, Volley, or Ktor)، يرجى مراعاة ما يلي:

### 1. عنوان الـ API (Base URL)
*   **المحاكي (Emulator):** استخدم `http://10.0.2.2:8000/api/` بدلاً من `localhost`.
*   **جهاز حقيقي:** استخدم عنوان الـ IP الخاص بجهاز الكمبيوتر (مثال: `http://192.168.1.5:8000/api/`).
*   **ملاحظة:** تأكد من إضافة `android:usesCleartextTraffic="true"` في ملف `AndroidManifest.xml` إذا لم تكن تستخدم HTTPS.

### 2. المصادقة (Authentication)
يعتمد النظام على **JWT (JSON Web Token)**. عند تسجيل الدخول، ستحصل على `access token`. يجب إرساله في كل طلب لاحق في الـ Header كالتالي:
```text
Authorization: Bearer <your_access_token>
```

### 3. التعامل مع الأخطاء (Unified Error Handling)
النظام يعيد الأخطاء بتنسيق موحد باللغتين العربية والإنجليزية. تأكد من عمل `Data Class` في الأندرويد لاستقبال هذا الهيكل:
```json
{
    "success": false,
    "error_code": "AUTH_001",
    "message": "رقم الهاتف أو كلمة المرور غير صحيحة",
    "message_en": "Invalid phone or password",
    "details": null,
    "timestamp": "2026-04-04T12:00:00Z"
}
```

### 4. رفع الصور (Multipart Requests)
عند إنشاء بلاغ جديد يحتوي على صور، استخدم `MultipartBody` لإرسال حقل `primary_photo` وبقية الصور في حقل `images`.

---

## 📖 التوثيق (Documentation)
بمجرد تشغيل السيرفر، يمكنك الوصول إلى التوثيق الكامل من المتصفح:
*   **Swagger UI:** [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/)
*   **ReDoc:** [http://127.0.0.1:8000/redoc/](http://127.0.0.1:8000/redoc/)

---

## ✨ المميزات الحالية
- [x] نظام معالجة استثناءات موحد (Global Error Handler).
- [x] حماية من الطلبات المتكررة (Rate Limiting).
- [x] توثيق كامل وأمثلة حية لكل كود خطأ.
- [x] نظام إحصائيات متقدم للوحات التحكم.
