from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.professionals.models import Professional
from tests.base import AuthenticatedAPITestCase


class DashboardMetricsTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="B")

        Lead.objects.create(professional=self.prof_a, name="L1", email="l1@teste.com", status=Lead.NEW)
        Lead.objects.create(professional=self.prof_a, name="L2", email="l2@teste.com", status=Lead.CONTACTED)
        Lead.objects.create(professional=self.prof_b, name="L3", email="l3@teste.com", status=Lead.NEW)

        self.client_a = Client.objects.create(professional=self.prof_a, name="C1")
        Client.objects.create(professional=self.prof_b, name="C2")

        now = timezone.now()
        Appointment.objects.create(
            professional=self.prof_a, client=self.client_a, starts_at=now, ends_at=now + timedelta(hours=1)
        )
        Appointment.objects.create(
            professional=self.prof_a,
            client=self.client_a,
            starts_at=now,
            ends_at=now + timedelta(hours=1),
            status=Appointment.CANCELLED,
        )

    def test_therapist_sees_only_own_metrics(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/dashboard/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["new_leads"], 1)
        self.assertEqual(data["active_clients"], 1)
        self.assertEqual(data["sessions_this_month"], 1)

    def test_admin_sees_global_metrics(self):
        self.login(self.admin)
        response = self.client.get("/api/v1/dashboard/metrics")
        data = response.json()["data"]
        self.assertEqual(data["new_leads"], 2)
        self.assertEqual(data["active_clients"], 2)

    def test_dashboard_alias_returns_same_shape(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_leads", response.json()["data"])

    def test_requires_authentication(self):
        response = self.client.get("/api/v1/dashboard/metrics")
        self.assertEqual(response.status_code, 401)
