from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token
from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.professionals.models import Professional


@override_settings(DEBUG=True)
class AuditLogAccessTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        log_action(self.admin, "create", "professional", 1)

    def _login(self, user):
        token = create_dev_token(user.firebase_uid, user.email, user.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_can_list_audit_logs(self):
        self._login(self.admin)
        response = self.client.get("/api/v1/audit-logs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_therapist_cannot_list_audit_logs(self):
        self._login(self.therapist)
        response = self.client.get("/api/v1/audit-logs")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_list_audit_logs(self):
        response = self.client.get("/api/v1/audit-logs")
        self.assertEqual(response.status_code, 401)


@override_settings(DEBUG=True)
class AuditEventsRecordedTests(APITestCase):
    """Confirma que eventos relevantes (docs/back.md secao 11: "auditoria
    gravando eventos relevantes") realmente geram um AuditLog, nao so que
    o endpoint de leitura existe."""

    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        token = create_dev_token(self.admin.firebase_uid, self.admin.email, self.admin.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_professional_create_is_audited(self):
        response = self.client.post(
            "/api/v1/professionals",
            {"user": self.therapist.id, "slug": "terapeuta-a", "full_name": "Terapeuta A"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        log = AuditLog.objects.get(resource="professional", action="create")
        self.assertEqual(log.user, self.admin)
        self.assertEqual(log.resource_id, str(response.json()["data"]["id"]))

    def test_professional_delete_is_audited(self):
        professional = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        self.client.delete(f"/api/v1/professionals/{professional.id}")
        self.assertTrue(
            AuditLog.objects.filter(resource="professional", action="delete", resource_id=str(professional.id)).exists()
        )

    def test_lead_convert_is_audited(self):
        professional = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        lead = Lead.objects.create(professional=professional, name="Lead A", email="lead@teste.com")
        response = self.client.post(f"/api/v1/leads/{lead.id}/convert")
        self.assertEqual(response.status_code, 201)
        log = AuditLog.objects.get(resource="lead", action="convert")
        self.assertEqual(log.resource_id, str(lead.id))
        self.assertEqual(log.metadata["client_id"], response.json()["data"]["id"])

    def test_appointment_transition_is_audited(self):
        professional = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        client = Client.objects.create(professional=professional, name="Cliente A")
        now = timezone.now()
        appointment = Appointment.objects.create(
            professional=professional, client=client, starts_at=now, ends_at=now + timedelta(hours=1)
        )
        response = self.client.patch(f"/api/v1/appointments/{appointment.id}/confirm")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                resource="appointment", action="confirmed", resource_id=str(appointment.id)
            ).exists()
        )
