from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token
from apps.accounts.models import User


class MeEndpointTests(APITestCase):
    def _auth(self, role="THERAPIST", uid="dev-user-1", email="user@teste.com"):
        token = create_dev_token(uid, email, role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return token

    def test_me_requires_authentication(self):
        response = self.client.get("/api/v1/me")
        self.assertEqual(response.status_code, 401)

    def test_me_rejects_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer lixo.invalido.token")
        response = self.client.get("/api/v1/me")
        self.assertEqual(response.status_code, 401)

    @override_settings(DEBUG=True)
    def test_dev_token_provisions_user_lazily(self):
        self._auth(role="ADMIN", uid="dev-admin-1", email="admin@teste.com")
        self.assertEqual(User.objects.count(), 0)

        response = self.client.get("/api/v1/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(response.json()["data"]["role"], "ADMIN")
        self.assertEqual(response.json()["data"]["firebase_uid"], "dev-admin-1")

    @override_settings(DEBUG=True)
    def test_me_patch_updates_email(self):
        self._auth()
        response = self.client.patch(
            "/api/v1/me", {"email": "novo@teste.com"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["email"], "novo@teste.com")

    @override_settings(DEBUG=True)
    def test_me_patch_cannot_change_role(self):
        self._auth(role="THERAPIST")
        self.client.get("/api/v1/me")
        response = self.client.patch("/api/v1/me", {"role": "ADMIN"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get().role, "THERAPIST")

    @override_settings(DEBUG=False)
    def test_fake_token_endpoint_disabled_outside_debug(self):
        from rest_framework.test import APIRequestFactory

        from apps.accounts.views import FakeTokenView

        request = APIRequestFactory().post("/api/v1/dev/fake-token", {}, format="json")
        response = FakeTokenView.as_view()(request)
        self.assertEqual(response.status_code, 403)
