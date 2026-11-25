from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView
from core.api_views import *
from core.extra_views import DashboardView,IssueExcelExportView,IssuePdfExportView,WorkExcelExportView,WorkPdfExportView,SpaceQrView
from core.model3d_views import DxfModelGenerateView
router=DefaultRouter()
for prefix,view,name in [
("projects",ProjectViewSet,"project"),("buildings",BuildingViewSet,"building"),
("levels",LevelViewSet,"level"),("spaces",SpaceViewSet,"space"),("drawings",DrawingViewSet,"drawing"),
("issues",IssueViewSet,"issue"),("tasks",TaskViewSet,"task"),("photos",PhotoViewSet,"photo"),
("progress",ProgressViewSet,"progress"),("models3d",Model3DViewSet,"model3d"),("audit-logs",AuditLogViewSet,"audit-log"),("users",UserViewSet,"user")]:
    router.register(prefix,view,basename=name)
urlpatterns=[
 path("admin/",admin.site.urls),path("api/health/",HealthView.as_view()),path("api/about/",AboutView.as_view()),
 path("api/auth/token/",TokenObtainPairView.as_view()),path("api/auth/token/refresh/",TokenRefreshView.as_view()),
 path("api/auth/me/",CurrentUserView.as_view()),path("api/dashboard/",DashboardView.as_view()),
 path("api/reports/issues.xlsx",IssueExcelExportView.as_view()),path("api/reports/issues.pdf",IssuePdfExportView.as_view()),
 path("api/reports/<str:report_type>.xlsx",WorkExcelExportView.as_view()),path("api/reports/<str:report_type>.pdf",WorkPdfExportView.as_view()),
 path("api/spaces/<uuid:space_id>/qr/",SpaceQrView.as_view()),
 path("api/models3d/generate/",DxfModelGenerateView.as_view()),
 path("api/",include(router.urls)),path("api/schema/",SpectacularAPIView.as_view(),name="schema"),
 path("api/docs/",SpectacularSwaggerView.as_view(url_name="schema"),name="swagger-ui"),
]+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
