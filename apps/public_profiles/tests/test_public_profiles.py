from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token
from apps.accounts.models import User
from apps.professionals.models import Professional, Specialty
from apps.services.models import Service


@override_settings(DEBUG=True)
class PublicProfessionalProfileTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.other_therapist = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.specialty = Specialty.objects.create(name="Ansiedade")
        self.professional = Professional.objects.create(
            user=self.therapist,
            slug="terapeuta-publica",
            full_name="Terapeuta Publica",
            bio="Bio publica",
            is_public=True,
        )
        self.professional.specialties.add(self.specialty)
        Service.objects.create(
            professional=self.professional, name="Individual", duration_minutes=50, modality=Service.ONLINE
        )
        self.private_professional = Professional.objects.create(
            user=self.other_therapist, slug="terapeuta-privada", full_name="Privada", is_public=False
        )

    def _login(self, user):
        token = create_dev_token(user.firebase_uid, user.email, user.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_public_profile_visible_without_auth(self):
        response = self.client.get("/api/v1/public/professionals/terapeuta-publica")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["full_name"], "Terapeuta Publica")
        self.assertEqual(len(data["specialties"]), 1)
        self.assertEqual(len(data["services"]), 1)
        self.assertNotIn("phone", data)
        self.assertNotIn("user", data)

    def test_private_profile_returns_404(self):
        response = self.client.get("/api/v1/public/professionals/terapeuta-privada")
        self.assertEqual(response.status_code, 404)

    def test_unknown_slug_returns_404(self):
        response = self.client.get("/api/v1/public/professionals/nao-existe")
        self.assertEqual(response.status_code, 404)

    def test_therapist_updates_own_public_profile(self):
        self._login(self.therapist)
        response = self.client.patch(
            f"/api/v1/professionals/{self.professional.id}/public-profile",
            {"bio": "Nova bio publica", "is_public": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.bio, "Nova bio publica")
        self.assertFalse(self.professional.is_public)

    def test_therapist_cannot_update_others_public_profile(self):
        self._login(self.other_therapist)
        response = self.client.patch(
            f"/api/v1/professionals/{self.professional.id}/public-profile", {"bio": "Hackeado"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.bio, "Bio publica")

    def test_admin_can_update_any_public_profile(self):
        self._login(self.admin)
        response = self.client.patch(
            f"/api/v1/professionals/{self.professional.id}/public-profile", {"bio": "Editado pelo admin"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_cannot_update_public_profile(self):
        response = self.client.patch(
            f"/api/v1/professionals/{self.professional.id}/public-profile", {"bio": "X"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_public_profile_endpoint_is_rate_limited(self):
        for _ in range(30):
            response = self.client.get("/api/v1/public/professionals/terapeuta-publica")
            self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/v1/public/professionals/terapeuta-publica")
        self.assertEqual(response.status_code, 429)
