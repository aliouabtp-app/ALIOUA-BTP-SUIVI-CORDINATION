from django.db import connection, transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from . import models
from .serializers import *
from .permissions import RolePermission, AdminOnlyPermission

class HealthView(APIView):
    permission_classes=[AllowAny]; authentication_classes=[]
    @extend_schema(tags=["النظام"],summary="فحص الخادم")
    def get(self,request):
        with connection.cursor() as c: c.execute("SELECT 1"); c.fetchone()
        return Response({"status":"ok","database":"ok","service":"ALIOUA BTP API"})

class CurrentUserView(APIView):
    permission_classes=[IsAuthenticated]
    @extend_schema(tags=["المصادقة"],summary="بيانات المستخدم الحالي",responses=CurrentUserSerializer)
    def get(self,request): return Response(CurrentUserSerializer(request.user).data)

class AuditedViewSet(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated,RolePermission]
    write_roles=set(); entity=None; creator_field=None
    def perform_create(self,serializer):
        kwargs={self.creator_field:self.request.user} if self.creator_field else {}
        with transaction.atomic():
            obj=serializer.save(**kwargs)
            models.AuditLog.objects.create(user=self.request.user,action="CREATE",entity=self.entity or obj.__class__.__name__,entity_id=str(obj.pk),payload={"fields":list(serializer.validated_data)})
    def perform_update(self,serializer):
        with transaction.atomic():
            obj=serializer.save()
            models.AuditLog.objects.create(user=self.request.user,action="UPDATE",entity=self.entity or obj.__class__.__name__,entity_id=str(obj.pk),payload={"fields":list(serializer.validated_data)})
    def perform_destroy(self,obj):
        if not hasattr(obj,"is_deleted"):
            raise MethodNotAllowed("DELETE",detail="الحذف غير متاح لهذا السجل.")
        with transaction.atomic():
            obj.is_deleted=True; obj.deleted_at=timezone.now(); obj.save(update_fields=["is_deleted","deleted_at","updated_at"])
            models.AuditLog.objects.create(user=self.request.user,action="SOFT_DELETE",entity=self.entity or obj.__class__.__name__,entity_id=str(obj.pk),payload={})

class ProjectViewSet(AuditedViewSet):
    queryset=models.Project.objects.all(); serializer_class=ProjectSerializer; write_roles={"ADMIN","MANAGER"}
    search_fields=["name","client"]; filterset_fields=["status"]; ordering_fields=["name","start_date","created_at"]
class BuildingViewSet(AuditedViewSet):
    queryset=models.Building.objects.select_related("project"); serializer_class=BuildingSerializer; write_roles={"ADMIN","MANAGER","ENGINEER"}
    search_fields=["name"]; filterset_fields=["project"]
class LevelViewSet(AuditedViewSet):
    queryset=models.Level.objects.select_related("building","building__project"); serializer_class=LevelSerializer; write_roles={"ADMIN","MANAGER","ENGINEER"}
    search_fields=["name"]; filterset_fields=["building"]
class SpaceViewSet(AuditedViewSet):
    queryset=models.Space.objects.select_related("level","level__building"); serializer_class=SpaceSerializer; write_roles={"ADMIN","MANAGER","ENGINEER"}
    search_fields=["name"]; filterset_fields=["level","space_type"]
class DrawingViewSet(AuditedViewSet):
    queryset=models.Drawing.objects.select_related("level","uploaded_by"); serializer_class=DrawingSerializer; write_roles={"ADMIN","MANAGER","ENGINEER"}; creator_field="uploaded_by"
    search_fields=["title","original_filename"]; filterset_fields=["level","file_type"]
    def perform_create(self,s):
        f=s.validated_data["file"]
        with transaction.atomic():
            o=s.save(uploaded_by=self.request.user,original_filename=f.name,file_size=f.size)
            models.AuditLog.objects.create(user=self.request.user,action="CREATE",entity="Drawing",entity_id=str(o.pk),payload={"filename":f.name})
class IssueViewSet(AuditedViewSet):
    queryset=models.Issue.objects.select_related("space","assignee","created_by","drawing"); serializer_class=IssueSerializer
    write_roles={"ADMIN","MANAGER","ENGINEER","INSPECTOR"}; creator_field="created_by"
    search_fields=["title","description","space__name"]; filterset_fields=["status","priority","assignee","space"]; ordering_fields=["created_at","due_date","priority"]
    def perform_update(self,s):
        old=s.instance.status
        with transaction.atomic():
            o=s.save()
            if o.status=="CLOSED" and old!="CLOSED": o.closed_at=timezone.now()
            elif o.status!="CLOSED": o.closed_at=None
            o.save(update_fields=["closed_at","updated_at"])
            models.AuditLog.objects.create(user=self.request.user,action="UPDATE",entity="Issue",entity_id=str(o.pk),payload={"fields":list(s.validated_data)})
class TaskViewSet(AuditedViewSet):
    queryset=models.Task.objects.select_related("space","assignee","created_by"); serializer_class=TaskSerializer
    write_roles={"ADMIN","MANAGER","ENGINEER"}; creator_field="created_by"
    search_fields=["name","description","space__name"]; filterset_fields=["status","assignee","space"]; ordering_fields=["due_date","progress","created_at"]
class PhotoViewSet(AuditedViewSet):
    queryset=models.Photo.objects.select_related("issue","task","space","uploaded_by"); serializer_class=PhotoSerializer
    write_roles={"ADMIN","MANAGER","ENGINEER","INSPECTOR"}; creator_field="uploaded_by"
    filterset_fields=["issue","task","space"]
    def perform_create(self,s):
        from io import BytesIO
        from PIL import Image, ImageOps
        from django.core.files.base import ContentFile
        original=s.validated_data["image"]
        # ضغط الصورة وتصحيح اتجاهها قبل تخزينها لتقليل استهلاك مساحة الخادم.
        img=ImageOps.exif_transpose(Image.open(original))
        img.thumbnail((2000,2000))
        fmt=img.format or "JPEG"
        if fmt not in {"JPEG","PNG","WEBP"}: fmt="JPEG"
        if fmt=="JPEG" and img.mode not in {"RGB","L"}: img=img.convert("RGB")
        buffer=BytesIO()
        if fmt=="JPEG": img.save(buffer,format=fmt,quality=82,optimize=True)
        elif fmt=="WEBP": img.save(buffer,format=fmt,quality=82,method=6)
        else: img.save(buffer,format=fmt,optimize=True)
        ext={"JPEG":"jpg","PNG":"png","WEBP":"webp"}[fmt]
        compressed=ContentFile(buffer.getvalue(),name=original.name.rsplit(".",1)[0]+"."+ext)
        with transaction.atomic():
            o=s.save(uploaded_by=self.request.user,image=compressed,original_filename=original.name,file_size=compressed.size)
            models.AuditLog.objects.create(user=self.request.user,action="CREATE",entity="Photo",entity_id=str(o.pk),payload={"filename":original.name,"original_size":original.size,"stored_size":compressed.size})
class ProgressViewSet(AuditedViewSet):
    queryset=models.Progress.objects.select_related("space","updated_by"); serializer_class=ProgressSerializer
    write_roles={"ADMIN","MANAGER","ENGINEER"}; creator_field="updated_by"; http_method_names=["get","post","head","options"]
    filterset_fields=["space"]; ordering_fields=["updated_at","percent"]
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=models.AuditLog.objects.select_related("user"); serializer_class=AuditLogSerializer; permission_classes=[AdminOnlyPermission]
    filterset_fields=["action","entity","user"]; ordering_fields=["timestamp"]
class UserViewSet(AuditedViewSet):
    queryset=models.User.objects.all().order_by("full_name","email"); serializer_class=UserAdminSerializer; permission_classes=[AdminOnlyPermission]
    http_method_names=["get","post","put","patch","head","options"]; entity="User"
    search_fields=["email","full_name"]; filterset_fields=["role","is_active"]
