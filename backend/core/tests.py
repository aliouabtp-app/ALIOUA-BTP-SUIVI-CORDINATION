import os
import tempfile
import ezdxf
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from unittest.mock import patch
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient
from .models import User,Project,Building,Level,Space,Issue,Task,AuditLog
from .version import APP_VERSION, clean_commit, clean_build_date

class ApiFoundationTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        self.admin=User.objects.create_superuser(email="admin@test.local",password="StrongPass123!",full_name="Admin")
        self.viewer=User.objects.create_user(email="viewer@test.local",password="StrongPass123!",full_name="Viewer",role="VIEWER")
        self.inspector=User.objects.create_user(email="inspector@test.local",password="StrongPass123!",full_name="Inspector",role="INSPECTOR")
        self.project=Project.objects.create(name="Test Project")
        self.building=Building.objects.create(project=self.project,name="Building A")
        self.level=Level.objects.create(building=self.building,name="Ground")
        self.space=Space.objects.create(level=self.level,name="Room 1")
    def test_health_endpoint_is_public(self):
        r=self.client.get("/api/health/")
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.data["status"],"ok")
    def test_unauthenticated_api_is_denied(self):
        self.assertEqual(self.client.get("/api/projects/").status_code,401)
    def test_viewer_cannot_create_project(self):
        self.client.force_authenticate(self.viewer)
        r=self.client.post("/api/projects/",{"name":"Forbidden"},format="json")
        self.assertEqual(r.status_code,403)
    def test_admin_can_create_project_and_audit_it(self):
        self.client.force_authenticate(self.admin)
        r=self.client.post("/api/projects/",{"name":"Created"},format="json")
        self.assertEqual(r.status_code,201)
        self.assertTrue(AuditLog.objects.filter(entity="Project",action="CREATE").exists())
    def test_inspector_can_create_issue(self):
        self.client.force_authenticate(self.inspector)
        r=self.client.post("/api/issues/",{"space":str(self.space.id),"title":"تسرب ماء","description":"ملاحظة اختبار","priority":"HIGH"},format="json")
        self.assertEqual(r.status_code,201)
        self.assertEqual(Issue.objects.get(pk=r.data["id"]).created_by,self.inspector)
    def test_inspector_cannot_create_task(self):
        self.client.force_authenticate(self.inspector)
        r=self.client.post("/api/tasks/",{"space":str(self.space.id),"name":"مهمة غير مسموحة"},format="json")
        self.assertEqual(r.status_code,403)
    def test_viewer_can_read_but_not_change_issues(self):
        issue=Issue.objects.create(space=self.space,title="Existing issue",created_by=self.admin)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get("/api/issues/").status_code,200)
        r=self.client.patch(f"/api/issues/{issue.id}/",{"title":"Changed"},format="json")
        self.assertEqual(r.status_code,403)
    def test_task_progress_rejects_values_over_100(self):
        self.client.force_authenticate(self.admin)
        r=self.client.post("/api/tasks/",{"space":str(self.space.id),"name":"Invalid progress","progress":150},format="json")
        self.assertEqual(r.status_code,400)

    def test_inspector_cannot_delete_issue(self):
        issue=Issue.objects.create(space=self.space,title="Protected issue",created_by=self.admin)
        self.client.force_authenticate(self.inspector)
        response=self.client.delete(f"/api/issues/{issue.id}/")
        self.assertEqual(response.status_code,403)
        self.assertFalse(Issue.all_objects.get(pk=issue.id).is_deleted)

    def test_manager_can_soft_delete_issue(self):
        manager=User.objects.create_user(email="manager@test.local",password="StrongPass123!",full_name="Manager",role="MANAGER")
        issue=Issue.objects.create(space=self.space,title="Archive me",created_by=self.admin)
        self.client.force_authenticate(manager)
        response=self.client.delete(f"/api/issues/{issue.id}/")
        self.assertEqual(response.status_code,204)
        archived=Issue.all_objects.get(pk=issue.id)
        self.assertTrue(archived.is_deleted)
        self.assertTrue(AuditLog.objects.filter(entity="Issue",entity_id=str(issue.id),action="SOFT_DELETE").exists())

 
class VersionHelpersTests(SimpleTestCase):
    def test_clean_commit_accepts_hex_and_shortens(self):
        self.assertEqual(clean_commit("0123456789abcdef0123456789abcdef01234567"), "0123456789ab")
        self.assertEqual(clean_commit(" ABCDEF1 "), "abcdef1")

    def test_clean_commit_rejects_anything_else(self):
        for bad in ("", None, "unknown", "<script>alert(1)</script>", "abc", "xyz1234", "abcdef1\\nINJECT"):
            self.assertEqual(clean_commit(bad), "unknown")

    def test_clean_build_date(self):
        self.assertEqual(clean_build_date("2026-11-24"), "2026-11-24")
        self.assertEqual(clean_build_date("2026-11-24T09:30:00Z"), "2026-11-24T09:30:00Z")
        for bad in ("", None, "yesterday", "2026-11-24<b>"):
            self.assertIsNone(clean_build_date(bad))


class AboutEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_about_is_public_with_exact_fields(self):
        with patch.dict(os.environ, {"APP_COMMIT": "", "APP_BUILD_DATE": ""}):
            r = self.client.get("/api/about/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.data), {"app", "version", "commit", "build_date"})
        self.assertEqual(r.data["version"], APP_VERSION)
        self.assertEqual(r.data["commit"], "unknown")
        self.assertIsNone(r.data["build_date"])

    def test_about_reports_commit_and_date_from_environment(self):
        env = {"APP_COMMIT": "0123456789abcdef0123456789abcdef01234567", "APP_BUILD_DATE": "2026-11-24T09:30:00Z"}
        with patch.dict(os.environ, env):
            r = self.client.get("/api/about/")
        self.assertEqual(r.data["commit"], "0123456789ab")
        self.assertEqual(r.data["build_date"], "2026-11-24T09:30:00Z")

    def test_about_never_reflects_untrusted_environment_values(self):
        with patch.dict(os.environ, {"APP_COMMIT": "<script>x</script>", "APP_BUILD_DATE": "<b>x</b>"}):
            r = self.client.get("/api/about/")
        self.assertNotIn(b"script", r.content)
        self.assertEqual(r.data["commit"], "unknown")

    def test_openapi_version_matches_app_version(self):
        self.assertEqual(settings.SPECTACULAR_SETTINGS["VERSION"], APP_VERSION)


class DxfTo3DTests(SimpleTestCase):
    def test_dxf_wall_lines_generate_valid_glb(self):
        from .dxf_to_3d import generate_glb_from_dxf
        doc = ezdxf.new("R2010")
        doc.layers.new("A-WALL")
        doc.modelspace().add_line((0, 0), (5000, 0), dxfattribs={"layer": "A-WALL"})
        with tempfile.NamedTemporaryFile(suffix=".dxf") as temp:
            doc.saveas(temp.name)
            glb, wall_count, selected_layer = generate_glb_from_dxf(
                temp.name, units="MM", wall_height=3.0, wall_thickness=0.2
            )
        self.assertEqual(glb[:4], b"glTF")
        self.assertEqual(wall_count, 1)
        self.assertEqual(selected_layer, "A-WALL")
        import io, trimesh
        loaded = trimesh.load(io.BytesIO(glb), file_type="glb")
        self.assertAlmostEqual(float(loaded.bounds[1][1] - loaded.bounds[0][1]), 3.0, places=2)

    def test_dxf_generator_rejects_unsupported_units(self):
        from .dxf_to_3d import generate_glb_from_dxf
        with self.assertRaises(ValueError):
            generate_glb_from_dxf("unused.dxf", units="UNKNOWN")


class DxfModelApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(email="3d-admin@test.local", password="StrongPass123!", full_name="3D Admin")
        project = Project.objects.create(name="3D Test Project")
        building = Building.objects.create(project=project, name="Building")
        self.level = Level.objects.create(building=building, name="Ground")

    def test_admin_can_generate_and_list_glb_model(self):
        doc = ezdxf.new("R2010")
        doc.layers.new("A-WALL")
        doc.modelspace().add_line((0, 0), (4000, 0), dxfattribs={"layer": "A-WALL"})
        with tempfile.NamedTemporaryFile(suffix=".dxf") as temp:
            doc.saveas(temp.name)
            temp.seek(0)
            uploaded = SimpleUploadedFile("ground.dxf", temp.read(), content_type="application/dxf")
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.client.force_authenticate(user=self.admin)
            response = self.client.post("/api/models3d/generate/", {
                "file": uploaded, "level": str(self.level.pk), "title": "Ground floor",
                "units": "MM", "wall_height": "3", "wall_thickness": "0.2",
            }, format="multipart")
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data["wall_count"], 1)
            self.assertTrue(response.data["file"].endswith(".glb"))
            listing = self.client.get("/api/models3d/")
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(len(listing.data["results"]), 1)
