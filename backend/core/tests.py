from django.test import TestCase
from rest_framework.test import APIClient
from .models import User,Project,Building,Level,Space,Issue,Task,AuditLog

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
