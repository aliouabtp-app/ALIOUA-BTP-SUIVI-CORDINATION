# التشغيل المحلي على شبكة الشركة

## بدون Docker
- Backend: اتبع تعليمات backend/README.md وشغّل Django على 0.0.0.0:8000.
- Web: اتبع تعليمات web/README.md وشغّل Vite على 0.0.0.0:5173.
- على أجهزة الفريق، استخدم عنوان IP للحاسوب الذي يشغّل الخادم، ولا تستخدم 127.0.0.1 من الهاتف.

## Docker (اختياري ومجاني)
يتطلب Docker Engine أو Docker Desktop. أنشئ backend/.env من backend/.env.example، وضع مفتاحاً سرياً قوياً، واستبدل 192.168.1.10 بعنوان IP الفعلي للحاسوب في حقلي DJANGO_ALLOWED_HOSTS وCORS_ALLOWED_ORIGINS، ثم من جذر المشروع:
```bash
docker compose up --build
```
- الويب: http://localhost:5173
- API: http://localhost:8000/api/
- Swagger: http://localhost:8000/api/docs/

تخزن قاعدة SQLite والملفات في مجلدات backend المحلية عبر volumes. خذ نسخاً احتياطية منها. هذا إعداد تطوير محلي وليس إعداد إنتاج؛ لا تعرض Django runserver على الإنترنت.
