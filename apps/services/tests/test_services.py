from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token
from apps.accounts.models import User
from apps.professionals.models import Professional
from apps.services.models import Service


@override_settings(DEBUG=True)
class ServiceIsolationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="Terapeuta A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="Terapeuta B")
        self.service_a = Service.objects.create(
            professional=self.prof_a, name="Sessao individual", duration_minutes=50, modality=Service.ONLINE
        )
        self.service_b = Service.objects.create(
            professional=self.prof_b, name="Sessao casal", duration_minutes=60, modality=Service.IN_PERSON
        )

    def _login(self, user):
        token = create_dev_token(user.firebase_uid, user.email, user.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_therapist_lists_only_own_services(self):
        self._login(self.therapist_a)
        response = self.client.get("/api/v1/services")
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Sessao individual")

    def test_admin_lists_all_services(self):
        self._login(self.admin)
        response = self.client.get("/api/v1/services")
        self.assertEqual(len(response.json()["data"]), 2)

    def test_therapist_cannot_read_other_service(self):
        self._login(self.therapist_a)
        response = self.client.get(f"/api/v1/services/{self.service_b.id}")
        self.assertEqual(response.status_code, 404)

    def test_therapist_creates_service_for_self_automatically(self):
        self._login(self.therapist_a)
        response = self.client.post(
            "/api/v1/services",
            {"name": "Terapia em grupo", "duration_minutes": 90, "modality": "BOTH"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["professional"], self.prof_a.id)

    def test_therapist_cannot_create_service_for_another_professional(self):
        self._login(self.therapist_a)
        response = self.client.post(
            "/api/v1/services",
            {
                "professional": self.prof_b.id,
                "name": "Tentativa",
                "duration_minutes": 30,
                "modality": "ONLINE",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["professional"], self.prof_a.id)

    def test_admin_must_specify_professional_when_creating(self):
        self._login(self.admin)
        response = self.client.post(
            "/api/v1/services",
            {"name": "Sem dono", "duration_minutes": 30, "modality": "ONLINE"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_therapist_can_delete_own_service(self):
        self._login(self.therapist_a)
        response = self.client.delete(f"/api/v1/services/{self.service_a.id}")
        self.assertEqual(response.status_code, 204)

    def test_therapist_cannot_delete_others_service(self):
        self._login(self.therapist_a)
        response = self.client.delete(f"/api/v1/services/{self.service_b.id}")
        self.assertEqual(response.status_code, 404)
