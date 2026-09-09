from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.clients.models import Client
from apps.clinical_records.models import ClinicalRecord
from apps.professionals.models import Professional
from tests.base import AuthenticatedAPITestCase


class ClinicalRecordAccessTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="B")
        self.client_a = Client.objects.create(professional=self.prof_a, name="Cliente A")
        self.client_b = Client.objects.create(professional=self.prof_b, name="Cliente B")
        self.record_a = ClinicalRecord.objects.create(
            client=self.client_a, professional=self.prof_a, author=self.therapist_a, content="Conteudo sigiloso A"
        )

    def test_admin_cannot_list_clinical_records(self):
        self.login(self.admin)
        response = self.client.get("/api/v1/clinical-records")
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_read_clinical_record(self):
        self.login(self.admin)
        response = self.client.get(f"/api/v1/clinical-records/{self.record_a.id}")
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_create_clinical_record(self):
        self.login(self.admin)
        response = self.client.post(
            "/api/v1/clinical-records", {"client": self.client_a.id, "content": "x"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_therapist_of_another_client_cannot_read(self):
        self.login(self.therapist_b)
        response = self.client.get(f"/api/v1/clinical-records/{self.record_a.id}")
        self.assertEqual(response.status_code, 404)

    def test_therapist_of_another_client_lists_none(self):
        self.login(self.therapist_b)
        response = self.client.get("/api/v1/clinical-records")
        self.assertEqual(response.json()["data"], [])

    def test_responsible_therapist_can_read(self):
        self.login(self.therapist_a)
        response = self.client.get(f"/api/v1/clinical-records/{self.record_a.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["content"], "Conteudo sigiloso A")

    def test_therapist_cannot_create_record_for_another_therapists_client(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/clinical-records", {"client": self.client_b.id, "content": "x"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_therapist_creates_record_for_own_client(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/clinical-records", {"client": self.client_a.id, "content": "Nova evolucao"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["professional"], self.prof_a.id)
        self.assertEqual(data["author"], self.therapist_a.id)

    def test_therapist_cannot_delete_others_record(self):
        self.login(self.therapist_b)
        response = self.client.delete(f"/api/v1/clinical-records/{self.record_a.id}")
        self.assertEqual(response.status_code, 404)


class ClinicalRecordAppointmentLinkTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.prof = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        self.client_obj = Client.objects.create(professional=self.prof, name="Cliente A")
        now = timezone.now()
        self.appointment = Appointment.objects.create(
            professional=self.prof, client=self.client_obj, starts_at=now, ends_at=now + timedelta(hours=1)
        )
        self.login(self.therapist)

    def test_links_record_to_appointment(self):
        response = self.client.post(
            "/api/v1/clinical-records",
            {"client": self.client_obj.id, "appointment": self.appointment.id, "content": "Sessao registrada"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["appointment"], self.appointment.id)

    def test_cannot_link_same_appointment_twice(self):
        ClinicalRecord.objects.create(
            client=self.client_obj, professional=self.prof, author=self.therapist,
            appointment=self.appointment, content="Primeira",
        )
        response = self.client.post(
            "/api/v1/clinical-records",
            {"client": self.client_obj.id, "appointment": self.appointment.id, "content": "Segunda"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_filters_by_client(self):
        ClinicalRecord.objects.create(
            client=self.client_obj, professional=self.prof, author=self.therapist, content="Nota 1"
        )
        response = self.client.get(f"/api/v1/clinical-records?client={self.client_obj.id}")
        self.assertEqual(len(response.json()["data"]), 1)


class ClinicalRecordAuditTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.prof = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        self.client_obj = Client.objects.create(professional=self.prof, name="Cliente A")
        self.login(self.therapist)

    def test_create_view_update_delete_are_audited_without_content(self):
        create_resp = self.client.post(
            "/api/v1/clinical-records",
            {"client": self.client_obj.id, "content": "Conteudo super secreto"},
            format="json",
        )
        record_id = create_resp.json()["data"]["id"]

        self.client.get(f"/api/v1/clinical-records/{record_id}")
        self.client.patch(f"/api/v1/clinical-records/{record_id}", {"content": "Editado"}, format="json")
        self.client.delete(f"/api/v1/clinical-records/{record_id}")

        logs = AuditLog.objects.filter(resource="clinical_record", resource_id=str(record_id))
        actions = set(logs.values_list("action", flat=True))
        self.assertEqual(actions, {"create", "view", "update", "delete"})
        for log in logs:
            self.assertNotIn("secreto", str(log.metadata))
            self.assertNotIn("Editado", str(log.metadata))
            self.assertEqual(set(log.metadata.keys()), {"client_id"})
