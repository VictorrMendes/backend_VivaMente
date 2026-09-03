from apps.accounts.models import User
from apps.clients.models import Client
from apps.professionals.models import Professional
from tests.base import AuthenticatedAPITestCase


class ClientIsolationTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="Terapeuta A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="Terapeuta B")
        self.client_a = Client.objects.create(professional=self.prof_a, name="Cliente A")
        self.client_b = Client.objects.create(professional=self.prof_b, name="Cliente B")

    def test_therapist_lists_only_own_clients(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/clients")
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Cliente A")

    def test_therapist_cannot_read_other_client(self):
        self.login(self.therapist_a)
        response = self.client.get(f"/api/v1/clients/{self.client_b.id}")
        self.assertEqual(response.status_code, 404)

    def test_therapist_creates_client_for_self_automatically(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/clients", {"name": "Novo cliente", "email": "novo@teste.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["professional"], self.prof_a.id)

    def test_admin_lists_all_clients(self):
        self.login(self.admin)
        response = self.client.get("/api/v1/clients")
        self.assertEqual(len(response.json()["data"]), 2)
