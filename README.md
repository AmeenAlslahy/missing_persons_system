# 📚 توثيق كامل لنظام البحث عن المفقودين

## 🎯 نظرة عامة
نظام بحث ذكي عن المفقودين يعتمد على الذكاء الاصطناعي، يوفر منصة رقمية موحدة لربط أسر المفقودين بالمجتمع والمتطوعين، مع مراعاة الجوانب الإنسانية والأخلاقية والخصوصية.

## 📁 هيكل المشروع
```text
missing_persons_system/
├── config/                    # إعدادات Django
├── accounts/                  # إدارة المستخدمين والمصادقة
├── reports/                   # إدارة البلاغات
├── matching/                  # نظام المطابقة بالذكاء الاصطناعي
├── notifications/             # نظام الإشعارات
├── analytics/                 # الإحصائيات والتحليلات
├── templates/                 # قوالب HTML
├── static/                    # ملفات ثابتة
├── media/                     # ملفات رفع المستخدمين
├── requirements.txt           # المكتبات المطلوبة
└── manage.py                  # إدارة Django
```

## 🛠️ متطلبات التشغيل

### المتطلبات الأساسية
```bash
Python 3.8+
PostgreSQL 13+ أو SQL Server Express
```

### تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### ملف requirements.txt
```txt
Django==4.2.0
djangorestframework==3.14.0
django-cors-headers==3.14.0
djangorestframework-simplejwt==5.3.0
django-filter==23.2
drf-yasg==1.21.5
django-extensions==3.2.3
python-decouple==3.8
pillow==10.0.0

# قواعد البيانات (اختر واحداً)
psycopg2-binary==2.9.7          # لـ PostgreSQL
# mssql-django==2.1.0           # لـ SQL Server

# إضافات
pyodbc==5.0.1                   # لـ SQL Server
```

## ⚙️ الإعداد الأولي

### 1. إنشاء قاعدة البيانات

**PostgreSQL**
```sql
CREATE DATABASE missing_persons_db
    ENCODING 'UTF8'
    LC_COLLATE 'Arabic_Saudi Arabia.1256'
    LC_CTYPE 'Arabic_Saudi Arabia.1256'
    TEMPLATE template0;
```

**SQL Server**
```sql
CREATE DATABASE missing_persons_db
    COLLATE Arabic_CI_AS;
```

### 2. إعداد ملف .env
```env
# Django
SECRET_KEY=your-super-secret-key-change-this
DEBUG=True

# Database
DB_ENGINE=django.db.backends.postgresql  # أو mssql
DB_NAME=missing_persons_db
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email (اختياري)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 3. تطبيق الـ Migrations
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. تشغيل السيرفر
```bash
python manage.py runserver
```

---

## 🔗 APIs الرئيسية

### � التوثيق (Swagger)
يمكنك الوصول إلى توثيق API التفاعلي عبر:
*   **Swagger UI:** `/swagger/`
*   **ReDoc:** `/redoc/`

## �🔐 المصادقة (accounts)
Base URL: `/api/accounts/`

| الطريقة | المسار | الوصف |
|---------|--------|-------|
| POST | `register/` | تسجيل مستخدم جديد |
| POST | `login/` | تسجيل الدخول |
| POST | `logout/` | تسجيل الخروج |
| GET | `profile/` | الملف الشخصي |
| PUT | `profile/update/` | تحديث الملف الشخصي |

## 📋 البلاغات (reports)
Base URL: `/api/reports/`

| الطريقة | المسار | الوصف |
|---------|--------|-------|
| GET | `reports/` | قائمة البلاغات |
| POST | `reports/` | إنشاء بلاغ جديد |
| GET | `reports/{id}/` | تفاصيل بلاغ |
| GET | `stats/` | إحصائيات البلاغات |

## 🤖 المطابقة (matching)
Base URL: `/api/matching/`

| الطريقة | المسار | الوصف |
|---------|--------|-------|
| GET | `matches/` | قائمة المطابقات |
| POST | `matches/find_matches/` | البحث عن تطابقات |
| GET | `stats/` | إحصائيات المطابقة |

## 🔔 الإشعارات (notifications)
Base URL: `/api/notifications/`

| الطريقة | المسار | الوصف |
|---------|--------|-------|
| GET | `notifications/` | قائمة الإشعارات |
| GET | `preferences/` | تفضيلات الإشعارات |
| GET | `stats/` | إحصائيات الإشعارات |

## 📊 التحليلات (analytics)
Base URL: `/api/analytics/`

| الطريقة | المسار | الوصف |
|---------|--------|-------|
| GET | `dashboard/` | لوحة التحكم |
| GET | `reports/` | التقارير التحليلية |
| POST | `generate-report/` | إنشاء تقرير |

---

# 📊 توثيق تفصيلي لجميع APIs

## 📋 دليل المحتويات
1. [🔐 المصادقة والحسابات](#-المصادقة-والحسابات)
2. [📋 البلاغات](#-البلاغات)
3. [🤖 المطابقة](#-المطابقة)
4. [🔔 الإشعارات](#-الإشعارات)
5. [📊 التحليلات](#-التحليلات)

---

## 🔐 المصادقة والحسابات

### 1. تسجيل مستخدم جديد
**Endpoint:** `POST /api/accounts/register/`

**البيانات المطلوبة:**
```json
{
  "email": "user@example.com",
  "full_name": "أحمد محمد",
  "password": "Password@123",
  "confirm_password": "Password@123",
  "phone": "0501234567",
  "date_of_birth": "1990-01-01",
  "gender": "M"
}
```

**البيانات المرجعة (Success - 201):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "أحمد محمد",
    "national_id": null,
    "date_of_birth": "1990-01-01",
    "age": 34,
    "gender": "M",
    "phone": "0501234567",
    "user_role": "user",
    "verification_status": "pending",
    "trust_score": 0.0,
    "total_reports": 0,
    "resolved_reports": 0,
    "profile_picture": null,
    "date_joined": "2024-04-15T10:30:00Z",
    "last_login": null
  },
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "تم إنشاء الحساب بنجاح"
}
```

### 2. تسجيل الدخول
**Endpoint:** `POST /api/accounts/login/`

**البيانات المطلوبة:**
```json
{
  "email": "user@example.com",
  "password": "Password@123"
}
```

**البيانات المرجعة (Success - 200):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "أحمد محمد",
    "national_id": null,
    "date_of_birth": "1990-01-01",
    "age": 34,
    "gender": "M",
    "phone": "0501234567",
    "user_role": "user",
    "verification_status": "pending",
    "trust_score": 0.0,
    "total_reports": 0,
    "resolved_reports": 0,
    "profile_picture": null,
    "date_joined": "2024-04-15T10:30:00Z",
    "last_login": "2024-04-15T11:00:00Z"
  },
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "تم تسجيل الدخول بنجاح"
}
```

### 3. الملف الشخصي
**Endpoint:** `GET /api/accounts/profile/`

**البيانات المرجعة (Success - 200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "أحمد محمد",
  "national_id": null,
  "date_of_birth": "1990-01-01",
  "age": 34,
  "gender": "M",
  "phone": "0501234567",
  "user_role": "user",
  "verification_status": "pending",
  "trust_score": 0.0,
  "total_reports": 5,
  "resolved_reports": 3,
  "profile_picture": "/media/profiles/user1.jpg",
  "date_joined": "2024-04-15T10:30:00Z",
  "last_login": "2024-04-15T11:00:00Z"
}
```

---

## 📋 البلاغات

### 1. إنشاء بلاغ جديد
**Endpoint:** `POST /api/reports/`

**البيانات المطلوبة (مفقود):**
```json
{
  "report_type": "missing",
  "person_name": "سارة أحمد",
  "age": 25,
  "gender": "F",
  "nationality": "سعودية",
  "height": 165.5,
  "weight": 60.0,
  "body_build": "متوسط",
  "skin_color": "فاتح",
  "eye_color": "بني",
  "hair_color": "أسود",
  "hair_type": "مجعد",
  "distinctive_features": "ندبة صغيرة على الجبين الأيسر",
  "scars_marks": "ندبة على الذراع الأيمن",
  "tattoos": "لا يوجد",
  "last_seen_location": "مول الرياض، الحي الدبلوماسي",
  "last_seen_date": "2024-04-15",
  "last_seen_time": "14:30:00",
  "missing_from": "الرياض",
  "circumstances": "خرجت للتسوق ولم تعد",
  "contact_person": "أحمد محمد",
  "contact_phone": "0501234567",
  "contact_email": "ahmed@example.com",
  "contact_relationship": "أخ",
  "city": "الرياض",
  "district": "الحي الدبلوماسي",
  "latitude": 24.7136,
  "longitude": 46.6753,
  "primary_photo": "file"  // ملف الصورة (اختياري للإناث)
}
```

**البيانات المطلوبة (معثور عليه):**
```json
{
  "report_type": "found",
  "person_name": "شخص غير معروف",
  "age": 30,
  "gender": "M",
  "nationality": "غير معروف",
  "height": 175.0,
  "weight": 70.0,
  "body_build": "نحيف",
  "skin_color": "أسمر",
  "eye_color": "بني",
  "hair_color": "أسود",
  "hair_type": "مستقيم",
  "distinctive_features": "نظارة طبية",
  "scars_marks": "لا يوجد",
  "tattoos": "لا يوجد",
  "last_seen_location": "حديقة الملك عبدالله",
  "last_seen_date": "2024-04-15",
  "last_seen_time": "10:00:00",
  "found_location": "حديقة الملك عبدالله، حي العليا",
  "found_date": "2024-04-15",
  "current_location": "مستشفى الملك فيصل التخصصي",
  "health_condition": "بحالة جيدة، يعاني من فقدان الذاكرة",
  "contact_person": "إدارة المستشفى",
  "contact_phone": "0111234567",
  "contact_email": "",
  "contact_relationship": "",
  "city": "الرياض",
  "district": "حي العليا",
  "latitude": 24.6981,
  "longitude": 46.6788,
  "primary_photo": "file"  // ملف الصورة (إلزامي)
}
```

**البيانات المرجعة (Success - 201):**
```json
{
  "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "report_code": "MISS-2024-001",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "أحمد محمد"
  },
  "report_type": "missing",
  "person_name": "سارة أحمد",
  "age": 25,
  "age_display": "25 سنة",
  "gender": "F",
  "nationality": "سعودية",
  "primary_photo": "/media/reports/photos/sara_ahmed.jpg",
  "height": 165.5,
  "weight": 60.0,
  "body_build": "متوسط",
  "skin_color": "فاتح",
  "eye_color": "بني",
  "hair_color": "أسود",
  "hair_type": "مجعد",
  "distinctive_features": "ندبة صغيرة على الجبين الأيسر",
  "scars_marks": "ندبة على الذراع الأيمن",
  "tattoos": "لا يوجد",
  "last_seen_location": "مول الرياض، الحي الدبلوماسي",
  "last_seen_date": "2024-04-15",
  "last_seen_time": "14:30:00",
  "missing_from": "الرياض",
  "circumstances": "خرجت للتسوق ولم تعد",
  "contact_person": "أحمد محمد",
  "contact_phone": "0501234567",
  "contact_email": "ahmed@example.com",
  "contact_relationship": "أخ",
  "status": "pending",
  "requires_admin_review": false,
  "latitude": 24.7136,
  "longitude": 46.6753,
  "city": "الرياض",
  "district": "الحي الدبلوماسي",
  "full_address": "الحي الدبلوماسي، الرياض",
  "created_at": "2024-04-15T14:30:00Z",
  "updated_at": "2024-04-15T14:30:00Z",
  "images": []
}
```

### 2. قائمة البلاغات
**Endpoint:** `GET /api/reports/`

**Query Parameters:**
```text
?report_type=missing          // نوع البلاغ
?status=active               // الحالة
?city=الرياض                 // المدينة
?gender=M                    // الجنس
?min_age=20                  // الحد الأدنى للعمر
?max_age=40                  // الحد الأقصى للعمر
?search=أحمد                 // بحث نصي
?ordering=-created_at        // الترتيب
?page=1                      // الصفحة
?page_size=20                // حجم الصفحة
```

**البيانات المرجعة (Success - 200):**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/reports/?page=2",
  "previous": null,
  "results": [
    {
      "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "report_code": "MISS-2024-001",
      "user": "أحمد محمد",
      "report_type": "missing",
      "person_name": "سارة أحمد",
      "age": 25,
      "gender": "F",
      "last_seen_location": "مول الرياض، الحي الدبلوماسي",
      "last_seen_date": "2024-04-15",
      "contact_phone": "0501234567",
      "status": "active",
      "city": "الرياض",
      "district": "الحي الدبلوماسي",
      "created_at": "2024-04-15T14:30:00Z",
      "full_address": "الحي الدبلوماسي، الرياض",
      "primary_photo": "/media/reports/photos/sara_ahmed.jpg"
    }
  ]
}
```

### 3. تفاصيل بلاغ محدد
**Endpoint:** `GET /api/reports/{report_id}/`

**البيانات المرجعة (Success - 200):**
```json
{
  "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "report_code": "MISS-2024-001",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "أحمد محمد"
  },
  "report_type": "missing",
  "person_name": "سارة أحمد",
  "age": 25,
  "age_display": "25 سنة",
  "gender": "F",
  "nationality": "سعودية",
  "primary_photo": "/media/reports/photos/sara_ahmed.jpg",
  "height": 165.5,
  "weight": 60.0,
  "body_build": "متوسط",
  "skin_color": "فاتح",
  "eye_color": "بني",
  "hair_color": "أسود",
  "hair_type": "مجعد",
  "distinctive_features": "ندبة صغيرة على الجبين الأيسر",
  "scars_marks": "ندبة على الذراع الأيمن",
  "tattoos": "لا يوجد",
  "last_seen_location": "مول الرياض، الحي الدبلوماسي",
  "last_seen_date": "2024-04-15",
  "last_seen_time": "14:30:00",
  "missing_from": "الرياض",
  "circumstances": "خرجت للتسوق ولم تعد",
  "contact_person": "أحمد محمد",
  "contact_phone": "0501234567",
  "contact_email": "ahmed@example.com",
  "contact_relationship": "أخ",
  "status": "active",
  "requires_admin_review": false,
  "latitude": 24.7136,
  "longitude": 46.6753,
  "city": "الرياض",
  "district": "الحي الدبلوماسي",
  "review_notes": "",
  "created_at": "2024-04-15T14:30:00Z",
  "updated_at": "2024-04-15T14:30:00Z",
  "images": [
    {
      "id": 1,
      "image": "/media/reports/images/photo1.jpg",
      "image_url": "http://localhost:8000/media/reports/images/photo1.jpg",
      "face_detected": true,
      "quality_score": 85.5,
      "processing_status": "completed",
      "uploaded_at": "2024-04-15T14:30:00Z"
    }
  ],
  "full_address": "الحي الدبلوماسي، الرياض"
}
```

### 4. البحث المتقدم في البلاغات
**Endpoint:** `POST /api/reports/search/`

**البيانات المطلوبة:**
```json
{
  "query": "سارة",
  "report_type": "missing",
  "city": "الرياض",
  "gender": "F",
  "min_age": 20,
  "max_age": 30,
  "start_date": "2024-04-01",
  "end_date": "2024-04-30"
}
```

**البيانات المرجعة (Success - 200):**
```json
{
  "count": 10,
  "results": [
    {
      "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "report_code": "MISS-2024-001",
      "person_name": "سارة أحمد",
      "age": 25,
      "gender": "F",
      "last_seen_location": "مول الرياض، الحي الدبلوماسي",
      "last_seen_date": "2024-04-15",
      "city": "الرياض",
      "district": "الحي الدبلوماسي",
      "status": "active",
      "created_at": "2024-04-15T14:30:00Z",
      "primary_photo": "/media/reports/photos/sara_ahmed.jpg",
      "distinctive_features": "ندبة صغيرة على الجبين الأيسر"
    }
  ]
}
```

---

## 🤖 المطابقة

### 1. البحث عن تطابقات لبلاغ
**Endpoint:** `POST /api/matching/matches/find_matches/`

**البيانات المطلوبة:**
```json
{
  "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "match_type": "auto"
}
```

**البيانات المرجعة (Success - 200):**
```json
{
  "report": {
    "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "report_code": "MISS-2024-001",
    "person_name": "سارة أحمد"
  },
  "total_matches": 3,
  "matches": [
    {
      "report": {
        "report_id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
        "report_code": "FND-2024-015",
        "person_name": "سارة أحمد",
        "age": 25,
        "gender": "F",
        "last_seen_location": "حديقة الملك عبدالله",
        "last_seen_date": "2024-04-16",
        "city": "الرياض"
      },
      "similarity_score": 0.92,
      "confidence_score": 95.5,
      "already_matched": false
    },
    {
      "report": {
        "report_id": "c3d4e5f6-g7h8-9012-cdef-345678901234",
        "report_code": "FND-2024-023",
        "person_name": "سارة محمد",
        "age": 26,
        "gender": "F",
        "last_seen_location": "مستشفى  ",
        "last_seen_date": "2024-04-17",
        "city": "الرياض"
      },
      "similarity_score": 0.78,
      "confidence_score": 82.3,
      "already_matched": true
    }
  ]
}
```

### 2. قائمة المطابقات
**Endpoint:** `GET /api/matching/matches/`

**Query Parameters:**
```text
?match_status=pending        // حالة المطابقة
?confidence_level=high       // مستوى الثقة
?match_type=auto            // نوع المطابقة
?ordering=-similarity_score // الترتيب
```

**البيانات المرجعة (Success - 200):**
```json
{
  "count": 50,
  "next": "http://localhost:8000/api/matching/matches/?page=2",
  "previous": null,
  "results": [
    {
      "match_id": "m1n2o3p4-q5r6-7890-stuv-wxyz12345678",
      "missing_report": {
        "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "report_code": "MISS-2024-001",
        "person_name": "سارة أحمد",
        "age": 25,
        "gender": "F",
        "last_seen_location": "مول الرياض",
        "last_seen_date": "2024-04-15",
        "city": "الرياض"
      },
      "found_report": {
        "report_id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
        "report_code": "FND-2024-015",
        "person_name": "سارة أحمد",
        "age": 25,
        "gender": "F",
        "last_seen_location": "حديقة الملك عبدالله",
        "last_seen_date": "2024-04-16",
        "city": "الرياض"
      },
      "similarity_score": 0.92,
      "confidence_score": 95.5,
      "confidence_level": "very_high",
      "match_type": "auto",
      "match_status": "pending"
    }
  ]
}
```

### 3. مراجعة مطابقة
**Endpoint:** `POST /api/matching/matches/{match_id}/review/`

**البيانات المطلوبة:**
```json
{
  "decision": "accept",  // accept, reject, need_more_info
  "notes": "التشابه عالي جداً، الوجه متطابق",
  "false_positive": false,
  "evidence_links": [
    "https://example.com/evidence1.jpg",
    "https://example.com/evidence2.jpg"
  ]
}
```

**البيانات المرجعة (Success - 200):**
```json
{
  "message": "تم قبول المطابقة",
  "match": {
    "match_id": "m1n2o3p4-q5r6-7890-stuv-wxyz12345678",
    "match_status": "accepted",
    "reviewed_by": {
      "id": 2,
      "email": "admin@example.com",
      "full_name": "مدير النظام"
    },
    "reviewed_at": "2024-04-16T11:00:00Z"
  }
}
```

---

## 🔔 الإشعارات

### 1. قائمة الإشعارات
**Endpoint:** `GET /api/notifications/notifications/`

**Query Parameters:**
```text
?notification_type=match_found  // نوع الإشعار
?priority_level=urgent         // مستوى الأولوية
?is_read=false                // مقروء/غير مقروء
?ordering=-created_at         // الترتيب
```

**البيانات المرجعة (Success - 200):**
```json
{
  "count": 25,
  "results": [
    {
      "notification_id": "n1o2t3i4-f5i6-7890-cation-1234567890ab",
      "title": "تم العثور على تطابق محتمل",
      "message": "تم العثور على تطابق محتمل بين بلاغك عن سارة أحمد وشخص تم العثور عليه. درجة التشابه: 92%",
      "notification_type": "match_found",
      "priority_level": "high",
      "action_required": true,
      "action_url": "/matches/m1n2o3p4-q5r6-7890-stuv-wxyz12345678",
      "is_read": false,
      "created_at": "2024-04-16T10:35:00Z",
      "time_ago": "منذ 5 دقائق"
    }
  ]
}
```

### 2. تحديد الإشعارات كمقروءة
**Endpoint:** `POST /api/notifications/notifications/mark_as_read/`

**البيانات المطلوبة (خيار 1):**
```json
{
  "notification_ids": [
    "n1o2t3i4-f5i6-7890-cation-1234567890ab",
    "a2b3c4d5-e6f7-8901-ghij-2345678901cd"
  ]
}
```

**البيانات المطلوبة (خيار 2 - تحديد الكل):**
```json
{
  "read_all": true
}
```

**البيانات المرجعة (Success - 200):**
```json
{
  "message": "تم تحديد 2 إشعار كمقروء",
  "count": 2
}
```

---

## 📊 التحليلات

### 1. لوحة التحكم
**Endpoint:** `GET /api/analytics/dashboard/`

**البيانات المرجعة (Success - 200):**
```json
{
  "widgets": [
    {
      "widget_id": "w1d2g3e4-t5w6-7890-gets-1234567890ab",
      "widget_name": "إحصائيات اليوم",
      "widget_type": "metric",
      "data_source": "daily_stats",
      "widget_data": {
        "new_reports": 15,
        "new_matches": 8,
        "new_users": 5,
        "match_success_rate": 85.5
      }
    }
  ],
  "daily_stats": {
    "date": "2024-04-16",
    "total_reports": 150
  }
}
```

---

## 👥 أدوار المستخدمين

| الدور | الكود | الصلاحيات |
|-------|-------|-----------|
| المستخدم العادي | `user` | إنشاء بلاغ، استلام إشعارات |
| المتطوع | `volunteer` | نفس السابق + عرض تفاصيل أكثر، المشاركة في البحث |
| المشرف | `admin` | نفس السابق + مراجعة البلاغات، إدارة المستخدمين |
| المشرف الرئيسي | `super_admin` | كل الصلاحيات + إعدادات النظام |
