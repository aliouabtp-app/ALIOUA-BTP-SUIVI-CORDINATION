import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta:
        abstract = True

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class SoftDelete(TimeStamped):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        abstract = True

class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("البريد الإلكتروني مطلوب")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True); extra.setdefault("is_superuser", True); extra.setdefault("is_active", True); extra.setdefault("role", "ADMIN")
        if extra["is_staff"] is not True or extra["is_superuser"] is not True:
            raise ValueError("حساب المدير يجب أن يملك صلاحيات الإدارة")
        return self.create_user(email, password, **extra)

class User(AbstractUser, UUIDModel):
    class Role(models.TextChoices):
        ADMIN="ADMIN","مدير النظام"; MANAGER="MANAGER","مسير الشركة"; ENGINEER="ENGINEER","مهندس"; INSPECTOR="INSPECTOR","مراقب"; VIEWER="VIEWER","مشاهد"
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=160)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER, db_index=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()
    def __str__(self): return f"{self.full_name} ({self.email})"

class ActiveManager(models.Manager):
    def get_queryset(self): return super().get_queryset().filter(is_deleted=False)

class Project(SoftDelete, UUIDModel):
    class Status(models.TextChoices):
        PLANNING="PLANNING","قيد التخطيط"; ACTIVE="ACTIVE","نشط"; ON_HOLD="ON_HOLD","متوقف"; COMPLETED="COMPLETED","مكتمل"; CANCELLED="CANCELLED","ملغى"
    name=models.CharField(max_length=200); client=models.CharField(max_length=200,blank=True)
    start_date=models.DateField(null=True,blank=True); end_date=models.DateField(null=True,blank=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.PLANNING,db_index=True)
    objects=ActiveManager(); all_objects=models.Manager()
    class Meta: ordering=["name"]
    def __str__(self): return self.name

class Building(SoftDelete, UUIDModel):
    project=models.ForeignKey(Project,on_delete=models.PROTECT,related_name="buildings")
    name=models.CharField(max_length=160)
    objects=ActiveManager(); all_objects=models.Manager()
    class Meta:
        ordering=["name"]
        constraints=[models.UniqueConstraint(fields=["project","name"],condition=Q(is_deleted=False),name="uq_active_building_project_name")]

class Level(SoftDelete, UUIDModel):
    building=models.ForeignKey(Building,on_delete=models.PROTECT,related_name="levels")
    name=models.CharField(max_length=120)
    elevation=models.DecimalField(max_digits=8,decimal_places=3,null=True,blank=True)
    objects=ActiveManager(); all_objects=models.Manager()
    class Meta:
        ordering=["name"]
        constraints=[models.UniqueConstraint(fields=["building","name"],condition=Q(is_deleted=False),name="uq_active_level_building_name")]

class Space(SoftDelete, UUIDModel):
    class SpaceType(models.TextChoices):
        ROOM="ROOM","غرفة"; CORRIDOR="CORRIDOR","ممر"; OFFICE="OFFICE","مكتب"; BATHROOM="BATHROOM","حمام"; EXTERNAL="EXTERNAL","خارجي"; OTHER="OTHER","أخرى"
    level=models.ForeignKey(Level,on_delete=models.PROTECT,related_name="spaces")
    name=models.CharField(max_length=160); space_type=models.CharField(max_length=20,choices=SpaceType.choices,default=SpaceType.OTHER)
    qr_token=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    objects=ActiveManager(); all_objects=models.Manager()
    class Meta:
        ordering=["name"]
        constraints=[models.UniqueConstraint(fields=["level","name"],condition=Q(is_deleted=False),name="uq_active_space_level_name")]

class Drawing(SoftDelete, UUIDModel):
    class FileType(models.TextChoices): PDF="PDF","PDF"; IMAGE="IMAGE","صورة"
    level=models.ForeignKey(Level,on_delete=models.PROTECT,related_name="drawings")
    title=models.CharField(max_length=200); file=models.FileField(upload_to="drawings/%Y/%m/")
    file_type=models.CharField(max_length=10,choices=FileType.choices)
    original_filename=models.CharField(max_length=255,blank=True); file_size=models.PositiveBigIntegerField(default=0)
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="uploaded_drawings")
    objects=ActiveManager(); all_objects=models.Manager()

class Issue(SoftDelete, UUIDModel):
    class Priority(models.TextChoices): LOW="LOW","منخفضة"; MEDIUM="MEDIUM","متوسطة"; HIGH="HIGH","مرتفعة"; CRITICAL="CRITICAL","حرجة"
    class Status(models.TextChoices): OPEN="OPEN","مفتوحة"; IN_PROGRESS="IN_PROGRESS","قيد المعالجة"; CLOSED="CLOSED","مغلقة"
    space=models.ForeignKey(Space,on_delete=models.PROTECT,related_name="issues")
    drawing=models.ForeignKey(Drawing,on_delete=models.SET_NULL,null=True,blank=True,related_name="issues")
    # إحداثيات النقطة نسبية من 0 إلى 1 لتظل صحيحة مع تغيير حجم المخطط.
    plan_x=models.DecimalField(max_digits=6,decimal_places=5,null=True,blank=True,validators=[MinValueValidator(0),MaxValueValidator(1)])
    plan_y=models.DecimalField(max_digits=6,decimal_places=5,null=True,blank=True,validators=[MinValueValidator(0),MaxValueValidator(1)])
    title=models.CharField(max_length=220); description=models.TextField(blank=True)
    priority=models.CharField(max_length=12,choices=Priority.choices,default=Priority.MEDIUM,db_index=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.OPEN,db_index=True)
    assignee=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="assigned_issues")
    due_date=models.DateField(null=True,blank=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_issues")
    closed_at=models.DateTimeField(null=True,blank=True)
    objects=ActiveManager(); all_objects=models.Manager()
    class Meta: ordering=["-created_at"]

class Task(SoftDelete, UUIDModel):
    class Status(models.TextChoices): TODO="TODO","جديدة"; IN_PROGRESS="IN_PROGRESS","قيد التنفيذ"; DONE="DONE","مكتملة"; BLOCKED="BLOCKED","متوقفة"
    space=models.ForeignKey(Space,on_delete=models.PROTECT,related_name="tasks")
    name=models.CharField(max_length=220); description=models.TextField(blank=True)
    progress=models.PositiveSmallIntegerField(default=0,validators=[MinValueValidator(0),MaxValueValidator(100)])
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.TODO)
    assignee=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="assigned_tasks")
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_tasks")
    due_date=models.DateField(null=True,blank=True)
    objects=ActiveManager(); all_objects=models.Manager()
    class Meta: ordering=["due_date","name"]

class Photo(SoftDelete, UUIDModel):
    issue=models.ForeignKey(Issue,on_delete=models.CASCADE,null=True,blank=True,related_name="photos")
    task=models.ForeignKey(Task,on_delete=models.CASCADE,null=True,blank=True,related_name="photos")
    space=models.ForeignKey(Space,on_delete=models.CASCADE,null=True,blank=True,related_name="photos")
    image=models.ImageField(upload_to="photos/%Y/%m/")
    original_filename=models.CharField(max_length=255,blank=True); file_size=models.PositiveBigIntegerField(default=0)
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="uploaded_photos")
    objects=ActiveManager(); all_objects=models.Manager()
    def clean(self):
        if sum(bool(x) for x in (self.issue_id,self.task_id,self.space_id)) != 1:
            raise ValidationError("يجب ربط الصورة بملاحظة أو مهمة أو مساحة واحدة فقط.")

class Progress(TimeStamped, UUIDModel):
    space=models.ForeignKey(Space,on_delete=models.PROTECT,related_name="progress_records")
    percent=models.PositiveSmallIntegerField(validators=[MinValueValidator(0),MaxValueValidator(100)])
    note=models.CharField(max_length=500,blank=True)
    updated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="progress_updates")
    class Meta: ordering=["-updated_at"]

class AuditLog(UUIDModel):
    class Action(models.TextChoices): CREATE="CREATE","إنشاء"; UPDATE="UPDATE","تعديل"; SOFT_DELETE="SOFT_DELETE","حذف ناعم"; LOGIN="LOGIN","دخول"; SYNC="SYNC","مزامنة"
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="audit_events")
    action=models.CharField(max_length=20,choices=Action.choices)
    entity=models.CharField(max_length=80); entity_id=models.CharField(max_length=64)
    timestamp=models.DateTimeField(auto_now_add=True,db_index=True)
    payload=models.JSONField(default=dict,blank=True)
    class Meta: ordering=["-timestamp"]
