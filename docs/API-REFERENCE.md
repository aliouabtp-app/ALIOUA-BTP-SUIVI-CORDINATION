# مرجع واجهة API

المخطط التنفيذي الكامل متاح من الخادم بعد تشغيله:
- JSON OpenAPI: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`

كل المسارات التالية تحت `/api/` ما لم يذكر غير ذلك. أغلب المسارات تتطلب:
`Authorization: Bearer <access_token>`

## المصادقة والنظام

| Method | Path | الوصف |
|---|---|---|
| GET | `/health/` | فحص الخادم وقاعدة البيانات (عام) |
| GET | `/about/` | إصدار الخادم وcommit وتاريخ البناء (عام، بلا أسرار) لشاشة «حول التطبيق» |
| POST | `/auth/token/` | تسجيل الدخول بالبريد وكلمة المرور وإرجاع access/refresh |
| POST | `/auth/token/refresh/` | تجديد access token |
| GET | `/auth/me/` | بيانات المستخدم الحالي ودوره |
| GET | `/dashboard/` | مؤشرات المشروع والتقدم حسب الطابق |

## بيانات المشروع

| المورد | المسارات |
|---|---|
| المشاريع | `GET, POST /projects/` ثم `GET, PUT, PATCH, DELETE /projects/{id}/` |
| المباني | `/buildings/` |
| الطوابق | `/levels/` |
| المساحات | `/spaces/` |
| المخططات | `/drawings/` |
| الملاحظات | `/issues/` |
| المهام | `/tasks/` |
| الصور | `/photos/` |
| التقدم | `/progress/` |
| سجل التدقيق | `GET /audit-logs/` |
| المستخدمون | `/users/` |

تدعم قوائم الموارد pagination وحقول البحث/التصفية المعرفة على كل ViewSet. استخدم `?search=` للبحث، ومعاملات مثل `?status=OPEN` أو `?space=<uuid>` حيث يدعم المورد ذلك.

## التقارير وQR

| Method | Path | الناتج |
|---|---|---|
| GET | `/reports/issues.xlsx` | ملف Excel للملاحظات |
| GET | `/reports/issues.pdf` | ملف PDF للملاحظات |
| GET | `/spaces/{uuid}/qr/` | صورة PNG لرمز QR الخاص بالمساحة |



## النماذج ثلاثية الأبعاد (DXF → GLB)

| Method | Path | الوصف |
|---|---|---|
| GET | `/models3d/` | قائمة النماذج المرتبطة بالطوابق |
| POST | `/models3d/generate/` | رفع DXF وتوليد GLB محلياً |

طلب التوليد يستخدم `multipart/form-data` والحقول:
- `file`: ملف DXF فقط، بحد أقصى 20 MiB.
- `level`: UUID الطابق.
- `title`: اسم النموذج.
- `units`: واحدة من `MM`, `CM`, `M`, `IN`, `FT`.
- `wall_height`: ارتفاع الجدار بالمتر، من 1 إلى 10.
- `wall_thickness`: سماكة الجدار بالمتر، من 0.05 إلى 0.50.
- `layer_name`: اسم طبقة DXF اختياري؛ عند تركه فارغاً يكتشف الخادم طبقات الجدران المعروفة، أو يستخدم كل الخطوط إذا لم يجدها.

مثال مبسط للحقول:
```text
file=<plan.dxf>
level=<UUID>
title=Ground floor draft
units=MM
wall_height=3
wall_thickness=0.2
layer_name=A-WALL
```

الاستجابة تحتوي على `id`, `title`, `level`, `file` (رابط GLB)، `source_filename`, `source_layer`, `wall_count`, `units`, `wall_height`, `wall_thickness`, وبيانات الإنشاء.

**حدود التحويل:** النسخة الأولى تستخرج LINE وLWPOLYLINE وPOLYLINE وتحوّل كل قطعة خطية إلى جدار مستطيل. لا تستنتج الفتحات أو الأعمدة أو البلاطات أو المناسيب من الواجهات والمقاطع. النتيجة تصور أولي وليست نموذج BIM أو رسماً تنفيذياً. الصلاحية للإنشاء Admin وManager وEngineer؛ القراءة لأي مستخدم مصادق.
\n## أمثلة

تسجيل الدخول:
```json
{"email":"admin@alioua.local","password":"CHANGE_THIS_PASSWORD"}
```

إنشاء ملاحظة:
```json
{
  "space": "UUID-OF-SPACE",
  "drawing": "UUID-OF-FLOOR-DRAWING",
  "plan_x": "0.42000",
  "plan_y": "0.61000",
  "title": "مراجعة جودة التشطيب",
  "description": "توجد ملاحظة في التشطيب تحتاج إلى معالجة.",
  "priority": "HIGH",
  "status": "OPEN",
  "assignee": null,
  "due_date": "2026-12-01"
}
```

إنشاء مهمة:
```json
{
  "space": "UUID-OF-SPACE",
  "name": "إنهاء أعمال الدهان",
  "description": "",
  "progress": 40,
  "status": "IN_PROGRESS",
  "assignee": null,
  "due_date": "2026-12-03"
}
```

حقلا `plan_x` و`plan_y` إحداثيات نسبية بين 0 و1 لعرض دبوس الملاحظة فوق صورة المخطط المختار. لا ترسلها إذا لم تحدد موضعاً.

رفع صورة إلى ملاحظة (multipart/form-data): الحقول `issue=<uuid>` و`image=<file>`. الحد الأعلى للصورة 10 MiB، والصيغ JPG/JPEG/PNG/WEBP. الخادم يتحقق من المحتوى ويضغط الصورة قبل التخزين.

## صلاحيات مختصرة

- Admin: كل العمليات، وإدارة المستخدمين وسجل التدقيق.
- Manager: إنشاء وتعديل المشروع والمباني والطوابق والمساحات والمهام والملاحظات والتقدم والمخططات.
- Engineer: كتابة بيانات التنسيق والملاحظات والمهام والتقدم والمخططات.
- Inspector: إنشاء وتعديل الملاحظات ورفع الصور.
- Viewer: قراءة البيانات فقط.

هذه مصفوفة أولية للأدوار؛ عزل السجلات على مستوى المشروع والمستخدم لم يكتمل بعد. لا تستخدم النظام حالياً لبيانات عدة جهات مستقلة أو كبيئة إنتاج مفتوحة للإنترنت.
