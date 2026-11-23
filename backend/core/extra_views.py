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
from .models import Project,Issue,Task,Level,Space

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
        out=BytesIO(); pdf=canvas.Canvas(out,pagesize=A4); width,height=A4
        pdf.setTitle("ALIOUA BTP Issues Report")
        y=height-48
        pdf.setFont("Helvetica-Bold",16); pdf.drawString(42,y,"ALIOUA BTP - SITE ISSUES REPORT"); y-=28
        pdf.setFont("Helvetica",9); pdf.drawString(42,y,"Generated report | Issue title, priority, status, due date"); y-=24
        for issue in Issue.objects.select_related("space").order_by("-created_at")[:45]:
            line=f"{issue.created_at:%Y-%m-%d} | {issue.priority} | {issue.status} | {issue.title[:55]}"
            pdf.drawString(42,y,line); y-=15
            if y<45: pdf.showPage(); y=height-45; pdf.setFont("Helvetica",9)
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
