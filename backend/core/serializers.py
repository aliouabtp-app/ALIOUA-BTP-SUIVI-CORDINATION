from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from .models import User, Project, Building, Level, Space, Drawing, Issue, Task, Photo, Progress, AuditLog

class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User; fields=["id","email","full_name","role"]

class UserAdminSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True, required=False, min_length=10)
    class Meta:
        model=User; fields=["id","email","full_name","role","is_active","password","date_joined"]
        read_only_fields=["id","date_joined"]
    def create(self, validated_data):
        password=validated_data.pop("password",None)
        if not password: raise serializers.ValidationError({"password":"كلمة المرور مطلوبة."})
        user=User(**validated_data); user.set_password(password); user.save(); return user
    def update(self, instance, validated_data):
        password=validated_data.pop("password",None)
        for key,value in validated_data.items(): setattr(instance,key,value)
        if password: instance.set_password(password)
        instance.save(); return instance

class ProjectSerializer(serializers.ModelSerializer):
    class Meta: model=Project; fields="__all__"; read_only_fields=["id","created_at","updated_at","is_deleted","deleted_at","archived_at"]
class BuildingSerializer(serializers.ModelSerializer):
    class Meta: model=Building; fields="__all__"; read_only_fields=["id","created_at","updated_at","is_deleted","deleted_at","archived_at"]
class LevelSerializer(serializers.ModelSerializer):
    class Meta: model=Level; fields="__all__"; read_only_fields=["id","created_at","updated_at","is_deleted","deleted_at","archived_at"]
class SpaceSerializer(serializers.ModelSerializer):
    class Meta: model=Space; fields="__all__"; read_only_fields=["id","qr_token","created_at","updated_at","is_deleted","deleted_at","archived_at"]
class DrawingSerializer(serializers.ModelSerializer):
    class Meta: model=Drawing; fields="__all__"; read_only_fields=["id","uploaded_by","original_filename","file_size","created_at","updated_at","is_deleted","deleted_at","archived_at"]
    def validate_file(self, f):
        if f.size > 25*1024*1024: raise serializers.ValidationError("الحد الأقصى لحجم المخطط 25 ميغابايت.")
        ext=f.name.lower().rsplit(".",1)[-1]
        if ext not in {"pdf","png","jpg","jpeg","webp"}: raise serializers.ValidationError("الصيغ المسموحة PDF وPNG وJPG وWEBP.")
        if ext != "pdf":
            try:
                f.seek(0); im=Image.open(f); im.verify(); f.seek(0)
                if im.format not in {"PNG","JPEG","WEBP"}: raise serializers.ValidationError("محتوى الصورة غير مدعوم.")
            except (UnidentifiedImageError, OSError): raise serializers.ValidationError("الملف ليس صورة سليمة.")
        return f
class IssueSerializer(serializers.ModelSerializer):
    class Meta: model=Issue; fields="__all__"; read_only_fields=["id","created_by","closed_at","created_at","updated_at","is_deleted","deleted_at","archived_at"]
    def validate(self,attrs):
        current=self.instance
        space=attrs.get("space",getattr(current,"space",None))
        drawing=attrs.get("drawing",getattr(current,"drawing",None))
        x=attrs.get("plan_x",getattr(current,"plan_x",None))
        y=attrs.get("plan_y",getattr(current,"plan_y",None))
        if drawing and space and drawing.level_id!=space.level_id:
            raise serializers.ValidationError({"drawing":"يجب أن يكون المخطط تابعاً لطابق المساحة نفسها."})
        if (x is None)!=(y is None):
            raise serializers.ValidationError("يجب تحديد إحداثيي X وY معاً.")
        if (x is not None or y is not None) and drawing is None:
            raise serializers.ValidationError("اختر مخططاً قبل تحديد موقع الدبوس.")
        return attrs
class TaskSerializer(serializers.ModelSerializer):
    class Meta: model=Task; fields="__all__"; read_only_fields=["id","created_by","created_at","updated_at","is_deleted","deleted_at","archived_at"]
class PhotoSerializer(serializers.ModelSerializer):
    class Meta: model=Photo; fields="__all__"; read_only_fields=["id","uploaded_by","original_filename","file_size","created_at","updated_at","is_deleted","deleted_at","archived_at"]
    def validate_image(self, f):
        if f.size > 10*1024*1024: raise serializers.ValidationError("الحد الأقصى للصورة 10 ميغابايت.")
        ext=f.name.lower().rsplit(".",1)[-1]
        if ext not in {"jpg","jpeg","png","webp"}: raise serializers.ValidationError("الصيغ المسموحة JPG وPNG وWEBP.")
        try:
            f.seek(0); im=Image.open(f); fmt=im.format; im.verify(); f.seek(0)
            expected={"jpg":"JPEG","jpeg":"JPEG","png":"PNG","webp":"WEBP"}[ext]
            if fmt != expected: raise serializers.ValidationError("امتداد الملف لا يطابق محتواه.")
        except (UnidentifiedImageError,OSError): raise serializers.ValidationError("ملف الصورة غير صالح.")
        return f
    def validate(self, attrs):
        existing=self.instance
        links=[attrs.get("issue",getattr(existing,"issue",None)),attrs.get("task",getattr(existing,"task",None)),attrs.get("space",getattr(existing,"space",None))]
        if sum(x is not None for x in links)!=1: raise serializers.ValidationError("اربط الصورة بملاحظة أو مهمة أو مساحة واحدة فقط.")
        return attrs
class ProgressSerializer(serializers.ModelSerializer):
    class Meta: model=Progress; fields="__all__"; read_only_fields=["id","updated_by","updated_at"]
class AuditLogSerializer(serializers.ModelSerializer):
    class Meta: model=AuditLog; fields="__all__"
