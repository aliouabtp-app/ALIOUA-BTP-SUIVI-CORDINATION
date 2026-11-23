from datetime import date,timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import User,Project,Building,Level,Space,Issue,Task,Progress

class Command(BaseCommand):
    help="إنشاء بيانات تجريبية آمنة لمشروع ALIOUA BTP"
    @transaction.atomic
    def handle(self,*args,**kwargs):
        users={}
        for email,name,role in [
            ("admin@alioua.local","مدير النظام","ADMIN"),
            ("manager@alioua.local","مسير الشركة","MANAGER"),
            ("engineer@alioua.local","مهندس الموقع","ENGINEER")]:
            u,created=User.objects.get_or_create(email=email,defaults={"full_name":name,"role":role,"is_staff":role=="ADMIN","is_superuser":role=="ADMIN"})
            if created:
                u.set_password("ChangeMe123!")
                u.save(update_fields=["password"])
            users[role]=u
        p,_=Project.objects.get_or_create(name="مشروع تجريبي - ALIOUA BTP",defaults={"client":"عميل تجريبي","start_date":date.today(),"status":"ACTIVE"})
        b,_=Building.objects.get_or_create(project=p,name="المبنى الرئيسي")
        levels=[]
        for i,n in enumerate(["الطابق الأرضي","الطابق الأول","الطابق الثاني"]):
            x,_=Level.objects.get_or_create(building=b,name=n,defaults={"elevation":i*3}); levels.append(x)
        specs=[(0,"المدخل الرئيسي","OTHER"),(0,"قاعة الاستقبال","ROOM"),(1,"المكتب الإداري","OFFICE"),(1,"الممر الشرقي","CORRIDOR"),(2,"قاعة الاجتماعات","ROOM"),(2,"دورات المياه","BATHROOM")]
        spaces=[]
        for i,n,t in specs:
            x,_=Space.objects.get_or_create(level=levels[i],name=n,defaults={"space_type":t}); spaces.append(x)
        issue_specs=[("معالجة تشقق موضعي","HIGH",0),("استكمال دهان الجدار","MEDIUM",1),("مراجعة تثبيت الأبواب","MEDIUM",2),("إصلاح حافة الممر","LOW",3),("فحص إنارة القاعة","CRITICAL",4)]
        for title,priority,i in issue_specs:
            Issue.objects.get_or_create(space=spaces[i],title=title,defaults={"description":"ملاحظة تجريبية لاختبار النظام.","priority":priority,"assignee":users["ENGINEER"],"created_by":users["MANAGER"],"due_date":date.today()+timedelta(days=5)})
        for name,pct,i in [("تهيئة منطقة العمل",100,0),("إنجاز طبقة الأساس",75,1),("تركيب الأبواب",50,2),("إنهاء أعمال الممر",30,3),("اختبار الإنارة",0,4)]:
            Task.objects.get_or_create(space=spaces[i],name=name,defaults={"progress":pct,"status":"DONE" if pct==100 else ("IN_PROGRESS" if pct else "TODO"),"assignee":users["ENGINEER"],"created_by":users["MANAGER"],"due_date":date.today()+timedelta(days=7)})
        for i,s in enumerate(spaces): Progress.objects.get_or_create(space=s,percent=[100,75,50,30,0,0][i],defaults={"updated_by":users["MANAGER"],"note":"قيمة تجريبية"})
        self.stdout.write(self.style.SUCCESS("تم إنشاء مشروع تجريبي و3 طوابق و6 مساحات و5 ملاحظات و5 مهام و3 مستخدمين."))
        self.stdout.write("الحسابات: admin@alioua.local / manager@alioua.local / engineer@alioua.local")
        self.stdout.write("كلمة مرور الحسابات الجديدة: ChangeMe123! — للتجربة المحلية فقط، غيّرها فوراً.")
