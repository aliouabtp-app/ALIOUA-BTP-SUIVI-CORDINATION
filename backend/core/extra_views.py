from io import BytesIO
from django.http import HttpResponse
from django.db.models import Count,Avg,Q
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import qrcode
from .models import Project,Issue,Task,Progress,Level,Space

class DashboardView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        issues=Issue.objects.all(); tasks=Task.objects.all()
        by_level=[]
        for level in Level.objects.filter(building__project__is_deleted=False).select_related("building"):
            ids=Space.objects.filter(level=level).values_list("id",flat=True)
            agg=Task.objects.filter(space_id__in=ids).aggregate(avg=Avg("progress"))
            by_level.append({"level":level.name,"building":level.building.name,"progress":round(agg["avg"] or 0)})
        return Response({
            "projects":Project.objects.count(),
            "issues_open":issues.exclude(status="CLOSED").count(),
            "issues_late":issues.exclude(status="CLOSED").filter(due_date__lt=__import__("django.utils.timezone",fromlist=["now"]).now().date()).count(),
            "issues_closed":issues.filter(status="CLOSED").count(),
            "tasks_total":tasks.count(),"tasks_done":tasks.filter(status="DONE").count(),
            "tasks_average_progress":round(tasks.aggregate(v=Avg("progress"))["v"] or 0),
            "progress_by_level":by_level,
        })

class IssueExcelExportView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        wb=Workbook(); ws=wb.active; ws.title="Issues"
        ws.append(["Title","Description","Priority","Status","Space","Assignee","Due date","Created"])
        for x in Issue.objects.select_related("space","assignee").order_by("-created_at"):
            ws.append([x.title,x.description,x.priority,x.status,x.space.name,x.assignee.full_name if x.assignee else "",str(x.due_date or ""),x.created_at.strftime("%Y-%m-%d")])
        for col in ws.columns:
            letter=col[0].column_letter; ws.column_dimensions[letter].width=min(max(max(len(str(c.value or "")) for c in col)+2,12),45)
        out=BytesIO(); wb.save(out); out.seek(0)
        response=HttpResponse(out.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"]='attachment; filename="alioua-btp-issues.xlsx"'
        return response

class IssuePdfExportView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        from pathlib import Path
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        out=BytesIO(); pdf=canvas.Canvas(out,pagesize=A4); width,height=A4
        # خط DejaVu المجاني يدعم الحروف العربية؛ يُثبت في Dockerfile.
        candidates=[
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        ]
        font=next((p for p in candidates if p.exists()),None)
        if font:
            if "DejaVuArabic" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("DejaVuArabic",str(font)))
            arabic_font="DejaVuArabic"
        else:
            arabic_font="Helvetica"
        def rtl(value): return get_display(reshape(str(value)))
        pdf.setTitle("ALIOUA BTP Issues Report")
        y=height-48
        pdf.setFont("Helvetica-Bold",16); pdf.drawString(42,y,"ALIOUA BTP - SITE ISSUES REPORT"); y-=28
        pdf.setFont("Helvetica",9); pdf.drawString(42,y,"Issue register | Priority | Status | Due date"); y-=24
        for issue in Issue.objects.select_related("space").order_by("-created_at")[:45]:
            pdf.setFont("Helvetica",8)
            meta=f"{issue.created_at:%Y-%m-%d} | {issue.priority} | {issue.status} | {issue.due_date or '-'}"
            pdf.drawString(42,y,meta)
            pdf.setFont(arabic_font,9)
            pdf.drawRightString(width-42,y,rtl(issue.title[:65]))
            y-=17
            if y<45:
                pdf.showPage(); y=height-45
        pdf.save(); out.seek(0)
        response=HttpResponse(out.getvalue(),content_type="application/pdf")
        response["Content-Disposition"]='attachment; filename="alioua-btp-issues.pdf"'
        return response

class SpaceQrView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,space_id):
        space=get_object_or_404(Space,pk=space_id)
        payload=f"ALIOUA-BTP:SPACE:{space.id}:{space.qr_token}"
        img=qrcode.make(payload); out=BytesIO(); img.save(out,format="PNG"); out.seek(0)
        return HttpResponse(out.getvalue(),content_type="image/png")



class WorkExcelExportView(APIView):
    """تصدير المهام أو سجل تقدم المساحات إلى Excel."""
    permission_classes=[IsAuthenticated]
    def get(self,request,report_type):
        wb=Workbook(); ws=wb.active
        if report_type=="tasks":
            ws.title="Tasks"
            ws.append(["Task","Description","Space","Status","Progress %","Assignee","Due date"])
            rows=Task.objects.select_related("space","assignee").order_by("due_date","name")
            for x in rows:
                ws.append([x.name,x.description,x.space.name,x.status,x.progress,x.assignee.full_name if x.assignee else "",str(x.due_date or "")])
            filename="alioua-btp-tasks.xlsx"
        elif report_type=="progress":
            ws.title="Progress"
            ws.append(["Space","Level","Building","Progress %","Note","Updated by","Updated at"])
            rows=Progress.objects.select_related("space__level__building","updated_by").order_by("-updated_at")
            for x in rows:
                ws.append([x.space.name,x.space.level.name,x.space.level.building.name,x.percent,x.note,x.updated_by.full_name,x.updated_at.strftime("%Y-%m-%d %H:%M")])
            filename="alioua-btp-progress.xlsx"
        else:
            return Response({"detail":"نوع التقرير غير مدعوم."},status=404)
        for col in ws.columns:
            letter=col[0].column_letter
            ws.column_dimensions[letter].width=min(max(max(len(str(c.value or "")) for c in col)+2,12),45)
        out=BytesIO(); wb.save(out); out.seek(0)
        response=HttpResponse(out.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"]=f'attachment; filename="{filename}"'
        return response


class WorkPdfExportView(APIView):
    """تقرير PDF موجز للمهام أو تقدم المساحات."""
    permission_classes=[IsAuthenticated]
    def get(self,request,report_type):
        from pathlib import Path
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        out=BytesIO(); pdf=canvas.Canvas(out,pagesize=A4); width,height=A4
        candidates=[Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),Path("/usr/share/fonts/dejavu/DejaVuSans.ttf")]
        font=next((p for p in candidates if p.exists()),None)
        if font:
            if "DejaVuArabic" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("DejaVuArabic",str(font)))
            arabic_font="DejaVuArabic"
        else:
            arabic_font="Helvetica"
        def rtl(value): return get_display(reshape(str(value)))
        if report_type=="tasks":
            title="تقرير المهام"
            rows=Task.objects.select_related("space","assignee").order_by("due_date","name")
            filename="alioua-btp-tasks.pdf"
            values=lambda x:[x.name,x.space.name,x.status,f"{x.progress}%",x.due_date or "—"]
        elif report_type=="progress":
            title="تقرير تقدم المساحات"
            rows=Progress.objects.select_related("space__level__building","updated_by").order_by("-updated_at")
            filename="alioua-btp-progress.pdf"
            values=lambda x:[x.space.name,x.space.level.name,f"{x.percent}%",x.note or "—",x.updated_at.strftime("%Y-%m-%d")]
        else:
            return Response({"detail":"نوع التقرير غير مدعوم."},status=404)
        pdf.setTitle(title); y=height-48
        pdf.setFont(arabic_font,16); pdf.drawRightString(width-42,y,rtl("إتقان – ALIOUA BTP | "+title)); y-=32
        for item in rows[:300]:
            data=values(item)
            pdf.setFont(arabic_font,9)
            pdf.drawRightString(width-42,y,rtl(" | ".join(str(v) for v in data)[:130]))
            y-=18
            if y<45:
                pdf.showPage(); y=height-45
        pdf.save(); out.seek(0)
        response=HttpResponse(out.getvalue(),content_type="application/pdf")
        response["Content-Disposition"]=f'attachment; filename="{filename}"'
        return response
