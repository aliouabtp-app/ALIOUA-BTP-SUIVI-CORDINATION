from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User,Project,Building,Level,Space,Drawing,Issue,Task,Photo,Progress,AuditLog
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering=("email",); list_display=("email","full_name","role","is_active")
    fieldsets=((None,{"fields":("email","password")}),("المعلومات",{"fields":("full_name","role")}),("الصلاحيات",{"fields":("is_active","is_staff","is_superuser","groups","user_permissions")}))
    add_fieldsets=((None,{"classes":("wide",),"fields":("email","full_name","role","password1","password2")}),)
    search_fields=("email","full_name"); filter_horizontal=("groups","user_permissions")
for model in [Project,Building,Level,Space,Drawing,Issue,Task,Photo,Progress,AuditLog]:
    admin.site.register(model)
