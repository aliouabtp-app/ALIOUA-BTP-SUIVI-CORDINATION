# Backend — ALIOUA BTP

## إعداد وتشغيل محلي
يتطلب Python 3.11+، وجميع الحزم في requirements.txt مجانية ومفتوحة المصدر.

```bash
cd backend
python -m venv .venv
# Linux/macOS/Termux: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

ضع في .env قيمة DJANGO_SECRET_KEY عشوائية لا تقل عن 50 حرفاً. لا ترفع .env أو db.sqlite3 إلى Git. ثم:

```bash
python manage.py makemigrations core
python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

## API
- GET /api/health/
- POST /api/auth/token/ — البريد الإلكتروني وكلمة المرور
- POST /api/auth/token/refresh/
- GET /api/auth/me/
- CRUD: /api/projects/ وbuildings وlevels وspaces وdrawings وissues وtasks وphotos وprogress
- GET /api/audit-logs/ (مدير النظام فقط)
- إدارة المستخدمين: /api/users/ (مدير النظام فقط)
- OpenAPI: /api/schema/ وSwagger: /api/docs/

## صلاحيات مختصرة
القراءة تتطلب تسجيل الدخول. الكتابة حسب الدور في كل ViewSet. إدارة المستخدمين وسجل التدقيق لمدير النظام فقط. هذه نسخة تأسيسية؛ يجب إضافة عزل صلاحيات البيانات حسب المشروع قبل إتاحتها لأكثر من جهة أو مشروع مستقل.

## ملفات البيانات
SQLite وmedia محليان. خذ نسخاً احتياطية منتظمة من قاعدة البيانات ومجلد media. لا تضع أسرار الإنتاج أو بيانات حقيقية في المستودع.
