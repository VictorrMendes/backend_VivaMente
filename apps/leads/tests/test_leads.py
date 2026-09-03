from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token
from apps.accounts.models import User
from apps.leads.models import Lead
from apps.professionals.models import Professional
from apps.services.models import Service


@override_settings(DEBUG=True)
class LeadIsolationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(
            user=self.therapist_a, slug="terapeuta-a", full_name="Terapeuta A", is_public=True
        )
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="Terapeuta B")
        self.lead_a = Lead.objects.create(professional=self.prof_a, name="Lead A", email="lead-a@teste.com")
        self.lead_b = Lead.objects.create(professional=self.prof_b, name="Lead B", email="lead-b@teste.com")

    def _login(self, user):
        token = create_dev_token(user.firebase_uid, user.email, user.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_therapist_lists_only_own_leads(self):
        self._login(self.therapist_a)
        response = self.client.get("/api/v1/leads")
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Lead A")

    def test_admin_lists_all_leads(self):
        self._login(self.admin)
        response = self.client.get("/api/v1/leads")
        self.assertEqual(len(response.json()["data"]), 2)

    def test_therapist_cannot_read_other_lead(self):
        self._login(self.therapist_a)
        response = self.client.get(f"/api/v1/leads/{self.lead_b.id}")
        self.assertEqual(response.status_code, 404)

    def test_therapist_creates_lead_for_self_automatically(self):
        self._login(self.therapist_a)
        response = self.client.post(
            "/api/v1/leads", {"name": "Novo lead", "email": "novo@teste.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["professional"], self.prof_a.id)
        self.assertEqual(response.json()["data"]["status"], "NEW")

    def test_status_endpoint_advances_lead(self):
        self._login(self.therapist_a)
        response = self.client.patch(
            f"/api/v1/leads/{self.lead_a.id}/status", {"status": "CONTACTED"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.lead_a.refresh_from_db()
        self.assertEqual(self.lead_a.status, "CONTACTED")

    def test_therapist_cannot_set_status_of_others_lead(self):
        self._login(self.therapist_a)
        response = self.client.patch(
            f"/api/v1/leads/{self.lead_b.id}/status", {"status": "CONTACTED"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_create_lead_with_invalid_status_via_write_serializer(self):
        self._login(self.therapist_a)
        response = self.client.post(
            "/api/v1/leads",
            {"name": "X", "email": "x@teste.com", "status": "CONVERTED"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["status"], "NEW")

    def test_convert_creates_client_and_marks_lead_converted(self):
        from apps.clients.models import Client

        self._login(self.therapist_a)
        response = self.client.post(f"/api/v1/leads/{self.lead_a.id}/convert")
        self.assertEqual(response.status_code, 201)
        self.lead_a.refresh_from_db()
        self.assertEqual(self.lead_a.status, "CONVERTED")
        client = Client.objects.get(lead=self.lead_a)
        self.assertEqual(client.name, "Lead A")
        self.assertEqual(client.professional, self.prof_a)

    def test_cannot_convert_lead_twice(self):
        self._login(self.therapist_a)
        self.client.post(f"/api/v1/leads/{self.lead_a.id}/convert")
        response = self.client.post(f"/api/v1/leads/{self.lead_a.id}/convert")
        self.assertEqual(response.status_code, 400)

    def test_therapist_cannot_convert_others_lead(self):
        self._login(self.therapist_a)
        response = self.client.post(f"/api/v1/leads/{self.lead_b.id}/convert")
        self.assertEqual(response.status_code, 404)


@override_settings(DEBUG=True)
class PublicAppointmentRequestTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.professional = Professional.objects.create(
            user=self.therapist, slug="terapeuta-publica", full_name="Terapeuta Publica", is_public=True
        )
        self.private_professional = Professional.objects.create(
            user=User.objects.create(firebase_uid="ther-priv", email="priv@teste.com", role=User.THERAPIST),
            slug="terapeuta-privada",
            full_name="Terapeuta Privada",
            is_public=False,
        )
        self.service = Service.objects.create(
            professional=self.professional, name="Individual", duration_minutes=50, modality=Service.ONLINE
        )

    def test_creates_lead_without_auth(self):
        response = self.client.post(
            "/api/v1/public/appointment-requests",
            {
                "professionalSlug": "terapeuta-publica",
                "name": "Joao Silva",
                "email": "joao@teste.com",
                "phone": "+55 11 99999-9999",
                "message": "Gostaria de agendar",
                "service": self.service.id,
                "preferredSlot": "2026-09-10T14:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        lead = Lead.objects.get()
        self.assertEqual(lead.professional, self.professional)
        self.assertEqual(lead.status, "NEW")
        self.assertIn("Horário solicitado", lead.message)

    def test_generic_contact_without_service_or_slot(self):
        response = self.client.post(
            "/api/v1/public/appointment-requests",
            {"professionalSlug": "terapeuta-publica", "name": "Maria", "email": "maria@teste.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_rejects_unknown_professional_slug(self):
        response = self.client.post(
            "/api/v1/public/appointment-requests",
            {"professionalSlug": "nao-existe", "name": "X", "email": "x@teste.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_non_public_professional(self):
        response = self.client.post(
            "/api/v1/public/appointment-requests",
            {"professionalSlug": "terapeuta-privada", "name": "X", "email": "x@teste.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_service_from_another_professional(self):
        other_prof = Professional.objects.create(
            user=User.objects.create(firebase_uid="ther-c", email="c@teste.com", role=User.THERAPIST),
            slug="outro",
            full_name="Outro",
            is_public=True,
        )
        other_service = Service.objects.create(
            professional=other_prof, name="Outro servico", duration_minutes=30, modality=Service.ONLINE
        )
        response = self.client.post(
            "/api/v1/public/appointment-requests",
            {
                "professionalSlug": "terapeuta-publica",
                "name": "X",
                "email": "x@teste.com",
                "service": other_service.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_public_endpoint_is_rate_limited(self):
        # usa o rate real configurado (settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        # 10/min): SimpleRateThrottle le esse valor uma vez na importacao do
        # modulo, entao override_settings em runtime nao o afeta.
        payload = {"professionalSlug": "terapeuta-publica", "name": "X", "email": "x@teste.com"}
        for _ in range(10):
            response = self.client.post("/api/v1/public/appointment-requests", payload, format="json")
            self.assertEqual(response.status_code, 201)
        response = self.client.post("/api/v1/public/appointment-requests", payload, format="json")
        self.assertEqual(response.status_code, 429)
