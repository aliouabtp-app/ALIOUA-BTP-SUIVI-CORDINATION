# تطبيق Android

هذا تطبيق Flutter أولي لتسجيل الدخول، عرض الملاحظات المحلية، إنشاء ملاحظة والتقاط صورة وحفظها محلياً في SQLite، ثم محاولة مزامنة سجل الملاحظة عند توفر الخادم.

## تشغيل وبناء APK
1. ثبّت Flutter SDK وAndroid SDK مجاناً على حاسوب.
2. من هذا المجلد نفّذ `flutter pub get`.
3. شغّل الخادم على الشبكة المحلية واضبط العنوان:
   `flutter run --dart-define=API_BASE=http://192.168.x.x:8000/api`
4. لبناء APK:
   `flutter build apk --release --dart-define=API_BASE=http://192.168.x.x:8000/api`
5. الملف الناتج: `build/app/outputs/flutter-apk/app-release.apk`.

ملاحظة: حفظ الصورة محلياً متاح في هذه النسخة، لكن رفع الصورة مع المزامنة يحتاج استكمال endpoint وربط الصورة بعد إنشاء الملاحظة. كما يجب ضبط Android INTERNET وCAMERA/Photo Picker حسب إعدادات المشروع.
