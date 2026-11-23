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
import 'package:connectivity_plus/connectivity_plus.dart';

String apiBase = const String.fromEnvironment('API_BASE', defaultValue: 'http://127.0.0.1:8000/api');
const navy = Color(0xFF102C43), teal = Color(0xFF1677B8), cream = Color(0xFFF4F7F8);

Future<Database> openLocalDb() async {
  final root = await getDatabasesPath();
  return openDatabase(p.join(root, 'alioua_btp_local.db'), version: 1,
    onCreate: (db, version) async {
      await db.execute('''CREATE TABLE issues(
        local_id INTEGER PRIMARY KEY AUTOINCREMENT, server_id TEXT, title TEXT NOT NULL,
        description TEXT, space_id TEXT NOT NULL, priority TEXT NOT NULL,
        due_date TEXT, image_path TEXT, sync_status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL)''');
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
  @override void initState() { super.initState(); _loadToken(); }
  Future<void> _loadToken() async {
    final p = await SharedPreferences.getInstance();
    apiBase = p.getString('api_base') ?? apiBase;
    if (!mounted) return;\n    setState(() { token = p.getString('access'); loading = false; });
  }
  void _loggedIn(String value) async {
    final p = await SharedPreferences.getInstance(); await p.setString('access', value);
    setState(() => token = value);
  }
  @override Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false, title: 'ALIOUA BTP',
    theme: ThemeData(useMaterial3: true, scaffoldBackgroundColor: cream,
      colorScheme: ColorScheme.fromSeed(seedColor: teal, primary: teal),
      fontFamily: 'Roboto'),
    home: loading ? const Scaffold(body: Center(child: CircularProgressIndicator(color: teal))) : token == null ? LoginPage(onLogin: _loggedIn) : IssuesPage(token: token!, onLogout: () async {
      final p = await SharedPreferences.getInstance(); await p.remove('access'); if (mounted) setState(() => token = null);
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
  Future<void> _refresh() async { final db=await dbFuture; final data=await db.query('issues',orderBy:'local_id DESC'); if(mounted)setState(()=>rows=data); }
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
