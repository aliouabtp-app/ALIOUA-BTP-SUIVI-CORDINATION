# Web — React + Vite

```bash
npm install
cp .env.example .env
npm run dev
```

الواجهة تستعمل `/api` من نفس عنوان الموقع، ويقوم Vite بتمرير طلبات API إلى الخادم. عند التشغيل المحلي الافتراضي يكون الهدف `http://127.0.0.1:8000`. إذا كان Backend في حاوية Docker، اضبط `API_PROXY_TARGET=http://backend:8000` كما في docker-compose.

بهذا يمكن فتح واجهة الويب من هاتف داخل شبكة الشركة على عنوان حاسوب الخادم دون وضع عنوان API خاص بالهاتف. للبناء: `npm run build`، والناتج في dist/.
