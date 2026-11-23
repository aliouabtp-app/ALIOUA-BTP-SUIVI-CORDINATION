from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import User,Project,Building,Level,Space,Issue,AuditLog

class ApiFoundationTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        self.admin=User.objects.create_superuser(email="admin@test.local",password="StrongPass123!",full_name="Admin")
        self.viewer=User.objects.create_user(email="viewer@test.local",password="StrongPass123!",full_name="Viewer",role="VIEWER")
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
    def test_admin_can_create_project(self):
        self.client.force_authenticate(self.admin)
        r=self.client.post("/api/projects/",{"name":"Created"},format="json")
        self.assertEqual(r.status_code,201)
        self.assertTrue(AuditLog.objects.filter(entity="Project",action="CREATE").exists())
