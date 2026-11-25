import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/services.dart';
import 'package:package_info_plus/package_info_plus.dart';

String apiBase = const String.fromEnvironment('API_BASE', defaultValue: 'http://127.0.0.1:8000/api');
// تخزين JWT مشفر عبر Android Keystore بدلاً من SharedPreferences النصي.
const secureStorage = FlutterSecureStorage();
const navy = Color(0xFF102C43), teal = Color(0xFF1677B8), cream = Color(0xFFF4F7F8);

Future<Database> openLocalDb() async {
  final root = await getDatabasesPath();
  return openDatabase(p.join(root, 'alioua_btp_local.db'), version: 2,
    onCreate: (db, version) async {
      await db.execute('''CREATE TABLE issues(
        local_id INTEGER PRIMARY KEY AUTOINCREMENT, server_id TEXT, title TEXT NOT NULL,
        description TEXT, space_id TEXT NOT NULL, priority TEXT NOT NULL,
        due_date TEXT, image_path TEXT, sync_status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL)''');
      await db.execute('''CREATE TABLE tasks(
        local_id INTEGER PRIMARY KEY AUTOINCREMENT, server_id TEXT, name TEXT NOT NULL,
        description TEXT, space_id TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'TODO', due_date TEXT,
        sync_status TEXT NOT NULL DEFAULT 'pending_create', created_at TEXT NOT NULL)''');
      await db.execute('''CREATE TABLE spaces(
        id TEXT PRIMARY KEY, name TEXT NOT NULL)''');
    },
    onUpgrade: (db, oldVersion, newVersion) async {
      // ترقية قاعدة البيانات الحالية دون حذف ملاحظات المستخدم المحفوظة.
      if (oldVersion < 2) {
        await db.execute('''CREATE TABLE tasks(
          local_id INTEGER PRIMARY KEY AUTOINCREMENT, server_id TEXT, name TEXT NOT NULL,
          description TEXT, space_id TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'TODO', due_date TEXT,
          sync_status TEXT NOT NULL DEFAULT 'pending_create', created_at TEXT NOT NULL)''');
        await db.execute('''CREATE TABLE spaces(
          id TEXT PRIMARY KEY, name TEXT NOT NULL)''');
      }
    });
}

void main() {
  // التقاط أخطاء Flutter غير المعالجة وعرضها داخل التطبيق بدل الشاشة البيضاء.
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
  };
  ErrorWidget.builder = (details) => Material(
    color: cream,
    child: Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.warning_amber_rounded, color: Colors.deepOrange, size: 48),
          const SizedBox(height: 12),
          const Text('حدث خطأ في عرض الصفحة', textDirection: TextDirection.rtl,
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: navy)),
          const SizedBox(height: 8),
          Text(details.exceptionAsString(), textDirection: TextDirection.ltr,
            textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.blueGrey)),
        ]),
      ),
    ),
  );
  runApp(const AliouaApp());
}

class AliouaApp extends StatefulWidget {
  const AliouaApp({super.key});
  @override State<AliouaApp> createState() => _AliouaAppState();
}
class _AliouaAppState extends State<AliouaApp> {
  String? token;
  bool loading = true;
  @override void initState() { super.initState(); _loadToken(); }
  Future<void> _loadToken() async {
    final p = await SharedPreferences.getInstance();
    apiBase = p.getString('api_base') ?? apiBase;
    if (!mounted) return;
    final savedToken = await secureStorage.read(key: 'access');
    if (!mounted) return;
    setState(() { token = savedToken; loading = false; });
  }
  Future<void> _loggedIn(String value) async {
    await secureStorage.write(key: 'access', value: value);
    if (mounted) setState(() => token = value);
  }
  @override Widget build(BuildContext context) => MaterialApp(
    builder: (context, child) => Directionality(textDirection: TextDirection.rtl, child: child ?? const SizedBox.shrink()),
    debugShowCheckedModeBanner: false, title: 'ALIOUA BTP',
    theme: ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: cream,
      colorScheme: ColorScheme.fromSeed(seedColor: teal, primary: teal, surface: Colors.white),
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: navy, foregroundColor: Colors.white, elevation: 0,
        centerTitle: false, titleTextStyle: TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: Colors.white),
      ),
      cardTheme: CardTheme(
        color: Colors.white, elevation: 1, shadowColor: navy.withOpacity(.08),
        margin: const EdgeInsets.only(bottom: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true, fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: const BorderSide(color: Color(0xFFDCE5EA))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: const BorderSide(color: Color(0xFFDCE5EA))),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: const BorderSide(color: teal, width: 1.6)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: teal, foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(50),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(backgroundColor: teal, foregroundColor: Colors.white),
    ),
    home: loading ? const Scaffold(body: Center(child: CircularProgressIndicator(color: teal))) : token == null ? LoginPage(onLogin: _loggedIn) : IssuesPage(token: token!, onLogout: () async {
      await secureStorage.delete(key: 'access'); if (mounted) setState(() => token = null);
    }));
}

class LoginPage extends StatefulWidget {
  final ValueChanged<String> onLogin;
  const LoginPage({super.key, required this.onLogin});
  @override State<LoginPage> createState() => _LoginPageState();
}
class _LoginPageState extends State<LoginPage> {
  final email = TextEditingController(), password = TextEditingController();
  final server = TextEditingController(text: apiBase);
  bool busy = false; String error = '';
  Future<void> submit() async {
    setState(() { busy = true; error = ''; });
    try {
      apiBase = server.text.trim().replaceAll(RegExp(r'/+$'), '');
      if (!apiBase.startsWith('http://') && !apiBase.startsWith('https://')) {
        throw Exception('أدخل عنوان API يبدأ بـ http أو https');
      }
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('api_base', apiBase);
      final r = await http.post(
        Uri.parse('$apiBase/auth/token/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email.text.trim(), 'password': password.text}),
      );
      if (r.statusCode != 200) {
        throw Exception('بيانات الدخول غير صحيحة أو الخادم غير متاح');
      }
      widget.onLogin(jsonDecode(r.body)['access'] as String);
    } catch (e) {
      if (mounted) setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }
  @override Widget build(BuildContext context) => Scaffold(body: Center(child: SingleChildScrollView(
    padding: const EdgeInsets.all(24), child: Card(elevation: 2, child: Padding(padding: const EdgeInsets.all(24),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.apartment_rounded, size: 48, color: teal),
        const SizedBox(height: 12), const Text('ALIOUA BTP', style: TextStyle(fontSize: 23,fontWeight: FontWeight.bold,color: navy)),
        const Text('متابعة وتنسيق الورش', style: TextStyle(color: Colors.blueGrey)),
        const SizedBox(height: 24),
        TextField(controller: server, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText:'عنوان الخادم API',hintText:'http://192.168.1.10:8000/api',border:OutlineInputBorder())),
        const SizedBox(height: 12),
        TextField(controller: email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText:'البريد الإلكتروني',border:OutlineInputBorder())),
        const SizedBox(height: 12),
        TextField(controller: password, obscureText:true, decoration: const InputDecoration(labelText:'كلمة المرور',border:OutlineInputBorder())),
        if(error.isNotEmpty) Padding(padding: const EdgeInsets.only(top:12),child:Text(error,style:const TextStyle(color:Colors.red))),
        const SizedBox(height: 18), SizedBox(width:double.infinity,child:FilledButton(onPressed:busy?null:submit,child:Text(busy?'جارٍ الدخول…':'تسجيل الدخول'))),
        const SizedBox(height: 4), TextButton(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const AboutPage())),child:const Text('حول التطبيق')),
      ]))))));
}

class IssuesPage extends StatefulWidget {
  final String token; final VoidCallback onLogout;
  const IssuesPage({super.key,required this.token,required this.onLogout});
  @override State<IssuesPage> createState()=>_IssuesPageState();
}
class _IssuesPageState extends State<IssuesPage> {
  late Future<Database> dbFuture; List<Map<String,Object?>> rows=[]; bool syncing=false;
  StreamSubscription<List<ConnectivityResult>>? connectionSub;
  @override void initState(){
    super.initState(); dbFuture=openLocalDb(); _refresh();
    // محاولة المزامنة تلقائياً عند عودة الاتصال؛ وتبقى البيانات محلية إذا تعذر الخادم.
    connectionSub=Connectivity().onConnectivityChanged.listen((states){
      if(states.any((s)=>s!=ConnectivityResult.none) && mounted) _sync();
    });
  }
  @override void dispose(){ connectionSub?.cancel(); super.dispose(); }
  Future<void> _refresh() async {
    final db=await dbFuture;
    // اعرض البيانات المحلية فوراً حتى لا ينتظر المستخدم الشبكة.
    final local=await db.query('issues',orderBy:'local_id DESC');
    if(mounted) setState(()=>rows=local);
    // ثم اجلب ملاحظات الخادم وأضفها محلياً دون المساس بالمسودات غير المزامنة.
    try {
      final response=await http.get(
        Uri.parse('$apiBase/issues/'),
        headers:{'Authorization':'Bearer ${widget.token}'},
      ).timeout(const Duration(seconds:12));
      if(response.statusCode!=200) return;
      final decoded=jsonDecode(response.body);
      final List<dynamic> remote=decoded is List ? decoded : (decoded['results'] as List? ?? []);
      for(final raw in remote) {
        if(raw is! Map<String,dynamic>) continue;
        final id=raw['id']?.toString();
        final spaceId=raw['space']?.toString();
        if(id==null || spaceId==null) continue;
        final existing=await db.query('issues',where:'server_id=?',whereArgs:[id],limit:1);
        final values={
          'server_id':id,
          'title':raw['title']?.toString() ?? 'ملاحظة بدون عنوان',
          'description':raw['description']?.toString() ?? '',
          'space_id':spaceId,
          'priority':raw['priority']?.toString() ?? 'MEDIUM',
          'due_date':raw['due_date']?.toString(),
          'sync_status':'synced',
          'created_at':raw['created_at']?.toString() ?? DateTime.now().toIso8601String(),
        };
        if(existing.isEmpty) {
          await db.insert('issues',values);
        } else {
          // لا نحدّث أي سجل محلي ما زال ينتظر رفعه.
          if(existing.first['sync_status']=='synced') {
            await db.update('issues',values,where:'server_id=?',whereArgs:[id]);
          }
        }
      }
      final refreshed=await db.query('issues',orderBy:'local_id DESC');
      if(mounted) setState(()=>rows=refreshed);
    } catch (_) {
      // عند انقطاع الشبكة نكتفي بالقائمة المحلية ولا نعرض خطأ يزعج المستخدم.
    }
  }
  Future<void> _sync() async {
    if(syncing || !mounted) return;
    setState(()=>syncing=true);
    try {
      final db=await dbFuture;
      final pending=await db.query('issues',where:"sync_status IN ('pending','photo_pending')");
      for(final item in pending){
        String serverId=(item['server_id'] as String?)??'';
        if(serverId.isEmpty){
          final body={'title':item['title'],'description':item['description'],'space':item['space_id'],'priority':item['priority'],'due_date':item['due_date']};
          final response=await http.post(Uri.parse('$apiBase/issues/'),headers:{'Authorization':'Bearer ${widget.token}','Content-Type':'application/json'},body:jsonEncode(body));
          if(response.statusCode!=201) continue;
          final data=jsonDecode(response.body); serverId=data['id'] as String;
          await db.update('issues',{'server_id':serverId,'sync_status':item['image_path']==null?'synced':'photo_pending'},where:'local_id=?',whereArgs:[item['local_id']]);
        }
        final imagePath=item['image_path'] as String?;
        if(imagePath!=null && imagePath.isNotEmpty){
          final req=http.MultipartRequest('POST',Uri.parse('$apiBase/photos/'));
          req.headers['Authorization']='Bearer ${widget.token}';
          req.fields['issue']=serverId;
          req.files.add(await http.MultipartFile.fromPath('image',imagePath));
          final streamed=await req.send();
          if(streamed.statusCode==201){
            await db.update('issues',{'sync_status':'synced'},where:'local_id=?',whereArgs:[item['local_id']]);
          }
        }
      }
      await _refresh();
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('انتهت المزامنة؛ تم الاحتفاظ بأي سجل لم يكتمل رفعه.')));
    } catch (_) {
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('تعذر الاتصال بالخادم؛ البيانات محفوظة محلياً وستتم إعادة المحاولة.')));
    } finally { if(mounted)setState(()=>syncing=false); }
  }
  Future<void> _newIssue() async {
    final result=await Navigator.push(context,MaterialPageRoute(builder:(_)=>NewIssuePage()));
    if(result==true) _refresh();
  }
  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(backgroundColor:navy,foregroundColor:Colors.white,title:const Text('ملاحظات الموقع'),actions:[
      IconButton(onPressed:syncing?null:_sync,icon:syncing?const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2,color:Colors.white)):const Icon(Icons.sync)),
      IconButton(tooltip:'المهام',onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>TasksPage(token:widget.token))),icon:const Icon(Icons.checklist_rounded)),
      IconButton(tooltip:'حول التطبيق',onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const AboutPage())),icon:const Icon(Icons.info_outline)),
      IconButton(onPressed:widget.onLogout,icon:const Icon(Icons.logout))
    ]),
    floatingActionButton:FloatingActionButton.extended(onPressed:_newIssue,backgroundColor:teal,foregroundColor:Colors.white,icon:const Icon(Icons.add),label:const Text('ملاحظة جديدة')),
    body:RefreshIndicator(onRefresh:_refresh,child:rows.isEmpty?ListView(children:const [SizedBox(height:180),Center(child:Text('لا توجد ملاحظات محفوظة بعد'))]):ListView.builder(padding:const EdgeInsets.all(14),itemCount:rows.length,itemBuilder:(c,i){
      final x=rows[i]; return Card(child:ListTile(leading:const CircleAvatar(backgroundColor:Color(0xFFE3F5F1),child:Icon(Icons.assignment_outlined,color:teal)),title:Text(x['title'] as String),subtitle:Text('${x['description']??''}\nالمساحة: ${x['space_id']}'),isThreeLine:true,trailing:Icon(x['sync_status']=='synced'?Icons.cloud_done:Icons.cloud_upload,color:x['sync_status']=='synced'?teal:Colors.orange)));
    })),
  );
}

class NewIssuePage extends StatefulWidget {
  @override State<NewIssuePage> createState()=>_NewIssuePageState();
}
class _NewIssuePageState extends State<NewIssuePage> {
  final title=TextEditingController(),description=TextEditingController(),space=TextEditingController();
  String priority='MEDIUM'; XFile? photo; bool saving=false;
  Future<void> scanSpace() async {
    final id=await Navigator.push<String>(context,MaterialPageRoute(builder:(_)=>const QrScanPage()));
    if(id!=null && mounted) setState(()=>space.text=id);
  }
  Future<void> pickPhoto() async {
    final x=await ImagePicker().pickImage(source:ImageSource.camera,imageQuality:75,maxWidth:1600);
    if(x!=null){
      // نقل الصورة من مجلد cache المؤقت إلى مجلد التطبيق الدائم قبل حفظ سجل الملاحظة.
      final dir=await getApplicationDocumentsDirectory();
      final saved=await File(x.path).copy(p.join(dir.path,'issue_${DateTime.now().millisecondsSinceEpoch}.jpg'));
      if(mounted)setState(()=>photo=XFile(saved.path));
    }
  }
  Future<void> save() async {
    if(title.text.trim().isEmpty||space.text.trim().isEmpty)return;
    setState(()=>saving=true);
    try{
      final db=await openLocalDb();
      await db.insert('issues',{'title':title.text.trim(),'description':description.text.trim(),'space_id':space.text.trim(),'priority':priority,'image_path':photo?.path,'sync_status':'pending','created_at':DateTime.now().toIso8601String()});
      if(mounted)Navigator.pop(context,true);
    }finally{if(mounted)setState(()=>saving=false);}
  }
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('تسجيل ملاحظة')),body:ListView(padding:const EdgeInsets.all(18),children:[
    TextField(controller:title,decoration:const InputDecoration(labelText:'عنوان الملاحظة',border:OutlineInputBorder())),
    const SizedBox(height:12),TextField(controller:description,maxLines:3,decoration:const InputDecoration(labelText:'الوصف',border:OutlineInputBorder())),
    const SizedBox(height:12),Row(children:[Expanded(child:TextField(controller:space,decoration:const InputDecoration(labelText:'المساحة / UUID',border:OutlineInputBorder()))),IconButton(tooltip:'مسح QR',onPressed:scanSpace,icon:const Icon(Icons.qr_code_scanner,color:teal,size:30))]),
    const SizedBox(height:12),DropdownButtonFormField(value:priority,decoration:const InputDecoration(labelText:'الأولوية',border:OutlineInputBorder()),items:const [DropdownMenuItem(value:'LOW',child:Text('منخفضة')),DropdownMenuItem(value:'MEDIUM',child:Text('متوسطة')),DropdownMenuItem(value:'HIGH',child:Text('مرتفعة')),DropdownMenuItem(value:'CRITICAL',child:Text('حرجة'))],onChanged:(v)=>setState(()=>priority=v??'MEDIUM')),
    const SizedBox(height:12),OutlinedButton.icon(onPressed:pickPhoto,icon:const Icon(Icons.camera_alt_outlined),label:Text(photo==null?'التقاط صورة':'تم إرفاق صورة')),
    if(photo!=null) Padding(padding:const EdgeInsets.only(top:8),child:Text(p.basename(photo!.path),textAlign:TextAlign.center)),
    const SizedBox(height:20),FilledButton(onPressed:saving?null:save,child:Text(saving?'جارٍ الحفظ…':'حفظ دون اتصال')),
    const SizedBox(height:8),const Text('تُحفظ الملاحظة على الجهاز أولاً. تحتاج المزامنة إلى معرّف مساحة صالح واتصال بالخادم.',style:TextStyle(color:Colors.blueGrey,fontSize:12))
  ]));
}

// ---------- إدارة المهام الميدانية ----------
class TasksPage extends StatefulWidget {
  final String token;
  const TasksPage({super.key, required this.token});
  @override State<TasksPage> createState() => _TasksPageState();
}
class _TasksPageState extends State<TasksPage> {
  List<Map<String,dynamic>> tasks=[];
  List<Map<String,dynamic>> spaces=[];
  bool loading=true, saving=false, syncing=false, offline=false;
  String error='';
  StreamSubscription<List<ConnectivityResult>>? connectionSub;

  @override void initState(){
    super.initState();
    _load();
    connectionSub=Connectivity().onConnectivityChanged.listen((states){
      if(states.any((s)=>s!=ConnectivityResult.none) && mounted) _sync();
    });
  }
  @override void dispose(){connectionSub?.cancel();super.dispose();}

  List<Map<String,dynamic>> _taskMaps(List<Map<String,Object?>> rows)=>rows.map((r)=>{
    'local_id':r['local_id'],'id':r['server_id']??'local_${r['local_id']}',
    'server_id':r['server_id'],'name':r['name'],'description':r['description']??'',
    'space':r['space_id'],'progress':r['progress']??0,'status':r['status']??'TODO',
    'due_date':r['due_date'],'sync_status':r['sync_status']??'synced',
  }).toList();

  Future<void> _load() async {
    if(mounted)setState(()=>loading=true);
    final db=await openLocalDb();
    final cachedSpaces=await db.query('spaces',orderBy:'name');
    final cachedTasks=await db.query('tasks',orderBy:'local_id DESC');
    if(mounted)setState((){
      spaces=cachedSpaces.map((x)=>Map<String,dynamic>.from(x)).toList();
      tasks=_taskMaps(cachedTasks);
      loading=false;
    });
    try{
      final headers={'Authorization':'Bearer ${widget.token}'};
      final responses=await Future.wait([
        http.get(Uri.parse('$apiBase/tasks/'),headers:headers),
        http.get(Uri.parse('$apiBase/spaces/'),headers:headers),
      ]).timeout(const Duration(seconds:12));
      if(responses.any((r)=>r.statusCode!=200))throw Exception('API');
      final taskBody=jsonDecode(responses[0].body),spaceBody=jsonDecode(responses[1].body);
      final remoteTasks=taskBody is List?taskBody:(taskBody['results'] as List? ?? []);
      final remoteSpaces=spaceBody is List?spaceBody:(spaceBody['results'] as List? ?? []);
      for(final raw in remoteSpaces){
        if(raw is Map && raw['id']!=null){
          await db.insert('spaces',{'id':raw['id'].toString(),'name':raw['name']?.toString()??'مساحة'},conflictAlgorithm:ConflictAlgorithm.replace);
        }
      }
      for(final raw in remoteTasks){
        if(raw is! Map || raw['id']==null || raw['space']==null)continue;
        final id=raw['id'].toString();
        final existing=await db.query('tasks',where:'server_id=?',whereArgs:[id],limit:1);
        if(existing.isNotEmpty && existing.first['sync_status']!='synced')continue;
        final values={
          'server_id':id,'name':raw['name']?.toString()??'مهمة',
          'description':raw['description']?.toString()??'','space_id':raw['space'].toString(),
          'progress':(raw['progress'] as num?)?.toInt()??0,
          'status':raw['status']?.toString()??'TODO','due_date':raw['due_date']?.toString(),
          'sync_status':'synced','created_at':raw['created_at']?.toString()??DateTime.now().toIso8601String(),
        };
        if(existing.isEmpty){await db.insert('tasks',values);}
        else{await db.update('tasks',values,where:'local_id=?',whereArgs:[existing.first['local_id']]);}
      }
      final refreshedSpaces=await db.query('spaces',orderBy:'name');
      final refreshedTasks=await db.query('tasks',orderBy:'local_id DESC');
      if(mounted)setState((){
        spaces=refreshedSpaces.map((x)=>Map<String,dynamic>.from(x)).toList();
        tasks=_taskMaps(refreshedTasks);offline=false;error='';
      });
    }catch(_){
      if(mounted)setState(()=>offline=true);
    }
  }

  Future<void> _sync() async {
    if(syncing||!mounted)return;
    setState(()=>syncing=true);
    try{
      final db=await openLocalDb();
      final pending=await db.query('tasks',where:"sync_status IN ('pending_create','pending_update')",orderBy:'local_id');
      for(final item in pending){
        try{
          final serverId=item['server_id']?.toString()??'';
          final body=jsonEncode({
            'name':item['name'],'description':item['description']??'',
            'space':item['space_id'],'progress':item['progress']??0,
            'status':item['status']??'TODO','due_date':item['due_date'],
          });
          final headers={'Authorization':'Bearer ${widget.token}','Content-Type':'application/json'};
          if(serverId.isEmpty){
            final r=await http.post(Uri.parse('$apiBase/tasks/'),headers:headers,body:body).timeout(const Duration(seconds:12));
            if(r.statusCode!=201)continue;
            final id=jsonDecode(r.body)['id']?.toString();
            if(id!=null)await db.update('tasks',{'server_id':id,'sync_status':'synced'},where:'local_id=?',whereArgs:[item['local_id']]);
          }else{
            final r=await http.patch(Uri.parse('$apiBase/tasks/$serverId/'),headers:headers,body:body).timeout(const Duration(seconds:12));
            if(r.statusCode>=200&&r.statusCode<300)await db.update('tasks',{'sync_status':'synced'},where:'local_id=?',whereArgs:[item['local_id']]);
          }
        }catch(_){break;}
      }
      await _load();
    }finally{if(mounted)setState(()=>syncing=false);}
  }

  Future<void> _update(Map<String,dynamic> task,Map<String,dynamic> changes) async {
    final db=await openLocalDb();
    final localId=task['local_id'] as int?;
    if(localId==null)return;
    final values=<String,Object?>{};
    if(changes.containsKey('progress'))values['progress']=changes['progress'];
    if(changes.containsKey('status'))values['status']=changes['status'];
    final current=await db.query('tasks',where:'local_id=?',whereArgs:[localId],limit:1);
    if(current.isEmpty)return;
    values['sync_status']=current.first['server_id']==null?'pending_create':'pending_update';
    await db.update('tasks',values,where:'local_id=?',whereArgs:[localId]);
    final rows=await db.query('tasks',orderBy:'local_id DESC');
    if(mounted)setState(()=>tasks=_taskMaps(rows));
    if(!offline)await _sync();
  }

  Future<void> _newTask() async {
    final name=TextEditingController(),description=TextEditingController();
    String? spaceId;int progress=0;String status='TODO';
    final created=await showDialog<bool>(context:context,builder:(dialogContext)=>StatefulBuilder(builder:(context,setDialog)=>AlertDialog(
      title:const Text('إضافة مهمة ميدانية'),
      content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
        TextField(controller:name,decoration:const InputDecoration(labelText:'اسم المهمة')),
        const SizedBox(height:10),
        DropdownButtonFormField<String>(value:spaceId,decoration:const InputDecoration(labelText:'المساحة'),items:spaces.map((x)=>DropdownMenuItem(value:x['id'].toString(),child:Text(x['name']?.toString()??'مساحة'))).toList(),onChanged:(v)=>setDialog(()=>spaceId=v)),
        const SizedBox(height:10),
        TextField(controller:description,maxLines:2,decoration:const InputDecoration(labelText:'الوصف')),
        const SizedBox(height:12),
        Row(children:[const Text('الإنجاز'),const Spacer(),Text('$progress%')]),
        Slider(value:progress.toDouble(),min:0,max:100,divisions:20,onChanged:(v)=>setDialog(()=>progress=v.round())),
        DropdownButtonFormField<String>(value:status,decoration:const InputDecoration(labelText:'الحالة'),items:const [
          DropdownMenuItem(value:'TODO',child:Text('جديدة')),
          DropdownMenuItem(value:'IN_PROGRESS',child:Text('قيد التنفيذ')),
          DropdownMenuItem(value:'BLOCKED',child:Text('متوقفة')),
          DropdownMenuItem(value:'DONE',child:Text('مكتملة')),
        ],onChanged:(v)=>setDialog(()=>status=v??'TODO')),
      ])),
      actions:[TextButton(onPressed:()=>Navigator.pop(dialogContext,false),child:const Text('إلغاء')),FilledButton(onPressed:()=>Navigator.pop(dialogContext,true),child:const Text('حفظ'))],
    )));
    if(created!=true)return;
    if(name.text.trim().isEmpty||spaceId==null){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('أدخل اسم المهمة واختر المساحة.')));
      return;
    }
    setState(()=>saving=true);
    try{
      final db=await openLocalDb();
      final localId=await db.insert('tasks',{
        'name':name.text.trim(),'description':description.text.trim(),'space_id':spaceId,
        'progress':progress,'status':status,'sync_status':'pending_create',
        'created_at':DateTime.now().toIso8601String(),
      });
      final rows=await db.query('tasks',orderBy:'local_id DESC');
      if(mounted)setState(()=>tasks=_taskMaps(rows));
      if(!offline)await _sync();
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(offline?'حُفظت المهمة على الهاتف وستتم مزامنتها عند عودة الشبكة.':'تم حفظ المهمة.')));
    }catch(_){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('تعذر حفظ المهمة محلياً.')));
    }finally{if(mounted)setState(()=>saving=false);}
  }

  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('مهام الموقع'),actions:[
      IconButton(onPressed:loading?null:_load,icon:const Icon(Icons.refresh)),
      IconButton(onPressed:syncing?null:_sync,icon:syncing?const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2,color:Colors.white)):const Icon(Icons.sync)),
    ]),
    floatingActionButton:FloatingActionButton.extended(onPressed:saving||spaces.isEmpty?null:_newTask,icon:const Icon(Icons.add),label:const Text('مهمة جديدة')),
    body:RefreshIndicator(onRefresh:_load,child:loading?const Center(child:CircularProgressIndicator()):Column(children:[
      if(offline)Container(width:double.infinity,color:const Color(0xFFFFF1D8),padding:const EdgeInsets.all(10),child:const Text('وضع عدم الاتصال: المهام الجديدة والتعديلات محفوظة محلياً.',textAlign:TextAlign.center,style:TextStyle(color:Color(0xFF805D1B),fontSize:12))),
      Expanded(child:tasks.isEmpty?ListView(children:[const SizedBox(height:140),Center(child:Text(spaces.isEmpty?'اتصل بالخادم مرة واحدة لتحميل المساحات قبل العمل دون اتصال.':'لا توجد مهام مسجلة بعد.'))]):ListView.builder(
        padding:const EdgeInsets.all(14),itemCount:tasks.length,itemBuilder:(context,index){
          final task=tasks[index],progress=(task['progress'] as num?)?.toInt()??0,status=task['status']?.toString()??'TODO';
          final localPending=task['sync_status']!='synced';
          return Card(child:Padding(padding:const EdgeInsets.all(14),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            Row(children:[Expanded(child:Text(task['name']?.toString()??'مهمة',style:const TextStyle(fontWeight:FontWeight.bold,fontSize:15))),Text('$progress%',style:const TextStyle(color:teal,fontWeight:FontWeight.bold))]),
            if((task['description']??'').toString().isNotEmpty)Padding(padding:const EdgeInsets.only(top:5),child:Text(task['description'].toString(),style:const TextStyle(color:Colors.blueGrey,fontSize:12))),
            const SizedBox(height:10),
            ClipRRect(borderRadius:BorderRadius.circular(8),child:LinearProgressIndicator(value:progress/100,minHeight:8,backgroundColor:const Color(0xFFE7EEF1),color:teal)),
            const SizedBox(height:10),
            Row(children:[
              Expanded(child:DropdownButtonFormField<String>(value:status,decoration:const InputDecoration(isDense:true,labelText:'الحالة'),items:const [
                DropdownMenuItem(value:'TODO',child:Text('جديدة')),
                DropdownMenuItem(value:'IN_PROGRESS',child:Text('قيد التنفيذ')),
                DropdownMenuItem(value:'BLOCKED',child:Text('متوقفة')),
                DropdownMenuItem(value:'DONE',child:Text('مكتملة')),
              ],onChanged:(v){if(v!=null)_update(task,{'status':v});})),
              const SizedBox(width:12),
              IconButton(tooltip:'تعديل نسبة الإنجاز',onPressed:()=>showDialog<void>(context:context,builder:(ctx){
                double value=progress.toDouble();
                return StatefulBuilder(builder:(ctx,setDialog)=>AlertDialog(title:const Text('تحديث الإنجاز'),content:Column(mainAxisSize:MainAxisSize.min,children:[Text('${value.round()}%'),Slider(value:value,min:0,max:100,divisions:20,onChanged:(v)=>setDialog(()=>value=v))]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('إلغاء')),FilledButton(onPressed:(){Navigator.pop(ctx);_update(task,{'progress':value.round()});},child:const Text('تحديث'))]));
              }),icon:Icon(Icons.tune,color:teal)),
            ]),
            if(localPending)const Padding(padding:EdgeInsets.only(top:8),child:Text('محفوظ محلياً — ينتظر المزامنة',style:TextStyle(color:Colors.orange,fontSize:11))),
          ])));
        })),
    ])),
  );
}

class QrScanPage extends StatelessWidget {
  const QrScanPage({super.key});
  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('مسح رمز المساحة')),
    body:MobileScanner(onDetect:(capture){
      for(final barcode in capture.barcodes){
        final raw=barcode.rawValue;
        if(raw==null) continue;
        final parts=raw.split(':');
        if(parts.length>=4 && parts[0]=='ALIOUA-BTP' && parts[1]=='SPACE'){
          Navigator.of(context).pop(parts[2]);
          break;
        }
      }
    }),
  );
}

 
// ---------- حول التطبيق ----------
const appCommit = String.fromEnvironment('APP_COMMIT', defaultValue: 'unknown');

String _shortCommit(String? value) {
  if (value == null || value.isEmpty || value == 'unknown') return 'غير معروف';
  return value.length > 12 ? value.substring(0, 12) : value;
}

class AboutPage extends StatefulWidget {
  const AboutPage({super.key});
  @override State<AboutPage> createState() => _AboutPageState();
}
class _AboutPageState extends State<AboutPage> {
  String appVersion = '…';
  Map<String, dynamic>? server;
  String? checkedAt;
  bool loading = true, online = false;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    setState(() => loading = true);
    final info = await PackageInfo.fromPlatform();
    final prefs = await SharedPreferences.getInstance();
    final cached = prefs.getString('about_cache');
    if (cached != null) {
      try {
        final m = jsonDecode(cached) as Map<String, dynamic>;
        server = m['data'] as Map<String, dynamic>?;
        checkedAt = m['at'] as String?;
      } catch (_) {
        // تجاهل تخزين تالف؛ سيُستبدل عند أول نجاح.
      }
    }
    var reached = false;
    try {
      final r = await http.get(Uri.parse('$apiBase/about/')).timeout(const Duration(seconds: 8));
      if (r.statusCode == 200) {
        final data = jsonDecode(r.body) as Map<String, dynamic>;
        final now = DateTime.now().toIso8601String();
        await prefs.setString('about_cache', jsonEncode({'data': data, 'at': now}));
        server = data; checkedAt = now; reached = true;
      }
    } catch (_) {
      // دون اتصال: نعرض آخر قيم محفوظة إن وُجدت.
    }
    if (!mounted) return;
    setState(() { appVersion = '${info.version} (${info.buildNumber})'; online = reached; loading = false; });
  }
  String _summary() => [
    'ALIOUA BTP',
    'التطبيق: $appVersion',
    'commit التطبيق: ${_shortCommit(appCommit)}',
    'API: $apiBase',
    'إصدار الخادم: ${server?['version'] ?? 'غير معروف'}',
    'commit الخادم: ${_shortCommit(server?['commit'] as String?)}',
    'آخر فحص ناجح: ${checkedAt ?? 'لم يتم'}',
  ].join('\n');
  Widget _row(String label, String value) => ListTile(
    title: Text(label, style: const TextStyle(color: Colors.blueGrey, fontSize: 13)),
    subtitle: Align(
      alignment: AlignmentDirectional.centerStart,
      child: SelectableText(value, textDirection: TextDirection.ltr,
        style: const TextStyle(color: navy, fontSize: 15, fontWeight: FontWeight.w600)),
    ),
  );
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('حول التطبيق'), actions: [
      IconButton(tooltip: 'نسخ المعلومات', icon: const Icon(Icons.copy), onPressed: () async {
        await Clipboard.setData(ClipboardData(text: _summary()));
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم نسخ معلومات الإصدار.')));
      }),
      IconButton(tooltip: 'تحديث', icon: const Icon(Icons.refresh), onPressed: loading ? null : _load),
    ]),
    body: ListView(padding: const EdgeInsets.all(14), children: [
      Card(child: Column(children: [
        _row('إصدار التطبيق', appVersion),
        _row('commit التطبيق', _shortCommit(appCommit)),
      ])),
      Card(child: Column(children: [
        ListTile(
          leading: Icon(online ? Icons.cloud_done : Icons.cloud_off, color: online ? teal : Colors.orange),
          title: Text(loading ? 'جارٍ الفحص…' : online ? 'متصل بالخادم' : 'غير متصل — تُعرض آخر قيم معروفة'),
        ),
        _row('عنوان API', apiBase),
        _row('إصدار الخادم', '${server?['version'] ?? 'غير معروف'}'),
        _row('commit الخادم', _shortCommit(server?['commit'] as String?)),
        if (checkedAt != null) _row('آخر فحص ناجح', checkedAt!.substring(0, 19).replaceFirst('T', ' ')),
      ])),
    ]),
  );
}
