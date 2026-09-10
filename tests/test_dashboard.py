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

    def test_appointments_today_and_upcoming(self):
        future = timezone.now() + timedelta(days=1)
        future_appt = Appointment.objects.create(
            professional=self.prof_a, client=self.client_a, starts_at=future, ends_at=future + timedelta(hours=1)
        )
        self.login(self.therapist_a)
        data = self.client.get("/api/v1/dashboard/metrics").json()["data"]
        # o appointment do setUp comeca em "now" (no passado por alguns ms
        # quando a view roda seu proprio timezone.now()) - so garantimos que
        # ele conta em "hoje" e que o de amanha aparece em "proximos".
        self.assertEqual(data["appointments_today"], 1)
        upcoming_ids = {item["id"] for item in data["upcoming_appointments"]}
        self.assertIn(future_appt.id, upcoming_ids)

    def test_pending_payments_and_monthly_summary_shape(self):
        from apps.payments.models import Payment

        Payment.objects.create(
            professional=self.prof_a, client=self.client_a, amount="80.00",
            status=Payment.PENDING, receipt_number="RD1",
        )
        self.login(self.therapist_a)
        data = self.client.get("/api/v1/dashboard/metrics").json()["data"]
        self.assertEqual(data["pending_payments"], {"count": 1, "total": "80.00"})
        self.assertIn("received_total", data["monthly_summary"])
        self.assertIn("sessions_count", data["monthly_summary"])

    def test_recent_activity_reflects_own_actions_without_sensitive_data(self):
        self.login(self.therapist_a)
        self.client.post(
            "/api/v1/clients", {"name": "Novo Cliente", "email": "novo@teste.com"}, format="json"
        )
        data = self.client.get("/api/v1/dashboard/metrics").json()["data"]
        actions = {(item["action"], item["resource"]) for item in data["recent_activity"]}
        self.assertIn(("create", "client"), actions)
        self.assertNotIn("novo@teste.com", str(data["recent_activity"]))
