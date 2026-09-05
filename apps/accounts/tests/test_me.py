from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token
from apps.accounts.models import User


class MeEndpointTests(APITestCase):
    def _auth(self, role="THERAPIST", uid="dev-user-1", email="user@teste.com"):
        # A autenticacao nunca mais provisiona o User localmente (isso e
        # papel da API interna de sync do Oauth) - o teste simula que o
        # usuario ja foi sincronizado antes de logar.
        User.objects.update_or_create(
            firebase_uid=uid,
            defaults={"email": email, "role": role, "active": True},
        )
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
    def test_me_rejects_token_without_local_user(self):
        token = create_dev_token("ghost-uid", "ghost@teste.com", "THERAPIST")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(User.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_me_rejects_inactive_local_user(self):
        User.objects.create(
            firebase_uid="inactive-uid",
            email="x@teste.com",
            role="THERAPIST",
            active=False,
        )
        token = create_dev_token("inactive-uid", "x@teste.com", "THERAPIST")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/me")

        self.assertEqual(response.status_code, 401)

    @override_settings(DEBUG=True)
    def test_me_returns_local_user_after_dev_provisioning(self):
        self._auth(role="ADMIN", uid="dev-admin-1", email="admin@teste.com")

        response = self.client.get("/api/v1/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["role"], "ADMIN")
        self.assertEqual(response.json()["data"]["firebase_uid"], "dev-admin-1")

    @override_settings(DEBUG=True)
    def test_fake_token_endpoint_provisions_local_user(self):
        response = self.client.post(
            "/api/v1/dev/fake-token",
            {"role": "ADMIN", "uid": "dev-admin-2", "email": "admin2@teste.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(firebase_uid="dev-admin-2")
        self.assertEqual(user.role, "ADMIN")
        self.assertTrue(user.active)

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
