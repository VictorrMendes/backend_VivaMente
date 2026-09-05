import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

import jwt
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.internal_auth import SERVICE_AUDIENCE, SERVICE_ISSUER
from apps.accounts.models import IdentitySyncRequestLog, User

URL_TMPL = "/api/v1/internal/identity/users/{uid}"

# Par de teste (RS256) - nao e a chave real de nenhum ambiente, existe so
# pra este arquivo poder assinar tokens que a view valida com a publica.
TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDVFyT1aG85QMoA
NGoxM+SGZhyijU/Hj6av0Jq2C+muCa33h0qC7T3AKsK9LLnTzb6o2xZjc8KkCJ+j
FUs8W3dhlDO6DoWWBfwKHx3s+DtqeQBQrlI/eJd176jKECIRuNgQhWWGmwZ/jSSD
vijnIcwBwG3K9SlGTM7TIggqq8x/OjT4WfeXQxM1CU5ZOTQERbVXsD77podcrl7f
UHAM7Kj2PVUKMOPCLq7i5uOvK9C4CLiXJ7lSEjJt5FS/1vFFV4ld9c1fv9LVd+4x
qcIwlLwI0Oze9Yl8X0r/t1Vb9KlNs3EkGzC2frgAkS047qn9nUI0On6fd81AYC4u
Nq//XewrAgMBAAECggEAAnWoPPAAbZRKBYgfMkin0xSy9cLoa3NE3+TMq77NTWW8
b43qh1YyTzH97cFgaAmcsU/NdeRp3Qsm5mj/vhYlunYmFIvbmGrxkuRVq/COfchI
E0PenGXdU4l5aIRJ7LDngnlPFonkeSfQ/NnXXXw6iTZVF/GOB1TvA8HKf0OXxhDE
sFQpScQnfAS+YIxAUI/JaZPO++ZRGdEYhZgSDKtLRFVj/mZc1usonA7Ih4uMAPPZ
Uu2HI01ks4e22/JkHMLKN/T2TofwPPLofNNES2e3M/k0+NKGkL+dbKjPEXSJw36C
AviWxMqVFs+voX7Ymi7pHffJK2FNJqy6FkGbvlJM8QKBgQDzxKvCbSiq4J0YbJlk
JfeMFx6E9OJX1dctlzojj8yG6ekrjlMCv8L9hZzqlu1nIFViWOhWnK8x1/qDvnCG
Ic7R6eQ5up0HAKjMcZj1TpNYnfrqALPetcaTERkXC3jN/ICfUrP88FGSGVZW0A5X
tbfrQZfImenAPNPiwU/Ofocy7wKBgQDfyGaXvyTC9555lllxC2kjot6yKMrthB5n
7IOLzxatz4Dg7NRmfDMaOgnkNb0HfZ04WxAxb2OFjr54qbeeZY7/T0aye4Fy+D3N
jGWZN0iCtYN7VcIBIr3IIqfPsUzmFWOQFLotNyrLJvRZXjKnbAmAMqEg7ny977Nl
v+Qsco7qhQKBgBhx5Hd+0tEv7REB8u/kDsrxlpHmrLv6KbXcsGvYg74TvtorT4+7
AybBO1cbA3uP9oACQmpNFBR/gBOuCUKqKT9LoSNY315QZpz510jiNExyqzLEF0WC
HQOqd0WkVNzzMULI3FvFDakE+W+DNaz+AA+LaFkpdhNdBjJ7CDHA5nXpAoGBAM61
tZasWI/D3V4gtGPIj4j8dEsLhU9awB9tCKIHW8KXr0uVWCmGxkmOnP5xaTfXH3gk
HdQcOUjwbx7UXqlw1GMfXoWVsiB6D9SjwGGEAHXEpzwxHjCgX7/Ty0D9XLQXw80e
aE9F60CWrhUy/wVJtYj2u4HI6e8k0IjHdURdWYhlAoGBALYKxnOY8IdWVPQoNHXh
hRF7/uccuxsCd9ItcUWdBmgVtJrpYg7KdOTi3z+y3+ooeY/sKLpS8aDaMKquL7Mb
BmyejTZWel/VS8uL0x+FR7/OAfFNMoB00Qc6p4vuS+YIaAtBceDH36AG7qCBWvP/
D99iA1iHTDZ/qDTbZG3v+mWo
-----END PRIVATE KEY-----"""

TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1Rck9WhvOUDKADRqMTPk
hmYcoo1Px4+mr9Catgvprgmt94dKgu09wCrCvSy5082+qNsWY3PCpAifoxVLPFt3
YZQzug6FlgX8Ch8d7Pg7ankAUK5SP3iXde+oyhAiEbjYEIVlhpsGf40kg74o5yHM
AcBtyvUpRkzO0yIIKqvMfzo0+Fn3l0MTNQlOWTk0BEW1V7A++6aHXK5e31BwDOyo
9j1VCjDjwi6u4ubjryvQuAi4lye5UhIybeRUv9bxRVeJXfXNX7/S1XfuManCMJS8
CNDs3vWJfF9K/7dVW/SpTbNxJBswtn64AJEtOO6p/Z1CNDp+n3fNQGAuLjav/13s
KwIDAQAB
-----END PUBLIC KEY-----"""


def _service_token(scope="identity:sync", key=None, ttl_seconds=60, **overrides):
    now = timezone.now()
    payload = {
        "iss": SERVICE_ISSUER,
        "sub": "oauth-service",
        "aud": SERVICE_AUDIENCE,
        "scope": scope,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    payload.update(overrides)
    return jwt.encode(payload, key or TEST_PRIVATE_KEY, algorithm="RS256")


def _payload(**overrides):
    body = {
        "email": "ana@vivamenteterapias.com.br",
        "role": "THERAPIST",
        "active": True,
        "version": 1,
        "occurred_at": "2026-09-03T21:30:00Z",
    }
    body.update(overrides)
    return body


@override_settings(INTERNAL_SERVICE_JWT_PUBLIC_KEY=TEST_PUBLIC_KEY)
class IdentitySyncAuthTests(APITestCase):
    def test_put_without_token_is_rejected(self):
        response = self.client.put(
            URL_TMPL.format(uid="uid-1"), _payload(), format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_put_rejects_firebase_style_token(self):
        # token assinado com um segredo/issuer diferentes - simula um
        # Firebase ID Token real, que nao deve ser aceito aqui.
        bogus = jwt.encode({"uid": "someone"}, "outro-segredo", algorithm="HS256")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {bogus}")
        response = self.client.put(
            URL_TMPL.format(uid="uid-1"),
            _payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            HTTP_X_REQUEST_ID="req-1",
        )
        self.assertEqual(response.status_code, 401)

    def test_put_rejects_wrong_scope(self):
        token = _service_token(scope="something:else")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.put(
            URL_TMPL.format(uid="uid-1"),
            _payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            HTTP_X_REQUEST_ID="req-1",
        )
        self.assertEqual(response.status_code, 403)

    def test_put_rejects_expired_token(self):
        token = _service_token(ttl_seconds=-10)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.put(
            URL_TMPL.format(uid="uid-1"),
            _payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            HTTP_X_REQUEST_ID="req-1",
        )
        self.assertEqual(response.status_code, 401)


@override_settings(INTERNAL_SERVICE_JWT_PUBLIC_KEY=TEST_PUBLIC_KEY)
class IdentitySyncPutTests(APITestCase):
    def setUp(self):
        token = _service_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _put(self, uid, body, idempotency_key=None, request_id="req-1"):
        return self.client.put(
            URL_TMPL.format(uid=uid),
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY=idempotency_key or str(uuid.uuid4()),
            HTTP_X_REQUEST_ID=request_id,
        )

    def test_missing_idempotency_key_returns_400(self):
        response = self.client.put(
            URL_TMPL.format(uid="uid-1"),
            _payload(),
            format="json",
            HTTP_X_REQUEST_ID="req-1",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_request_id_returns_400(self):
        response = self.client.put(
            URL_TMPL.format(uid="uid-1"),
            _payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(response.status_code, 400)

    def test_creates_user_returns_201(self):
        response = self._put("uid-1", _payload())
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(firebase_uid="uid-1")
        self.assertEqual(user.role, "THERAPIST")
        self.assertTrue(user.active)
        self.assertEqual(user.identity_version, 1)

    def test_rejects_role_outside_admin_therapist(self):
        response = self._put("uid-1", _payload(role="SUPERUSER"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_repeated_idempotency_key_returns_cached_response_without_reprocessing(
        self,
    ):
        key = str(uuid.uuid4())
        first = self._put("uid-1", _payload(), idempotency_key=key)
        self.assertEqual(first.status_code, 201)

        # Corpo diferente, mesma Idempotency-Key: deve ser ignorado e
        # devolver a mesma resposta da primeira vez.
        second = self._put(
            "uid-1", _payload(role="ADMIN", version=2), idempotency_key=key
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(User.objects.get(firebase_uid="uid-1").role, "THERAPIST")

    def test_concurrent_same_idempotency_key_returns_winners_response(self):
        # Simula a corrida: duas requests com a mesma Idempotency-Key
        # passam pelo check inicial antes de qualquer uma commitar. A
        # segunda a chegar no INSERT final esbarra na unique constraint
        # (IntegrityError) e deve devolver a resposta que a vencedora
        # gravou, em vez de estourar 500.
        key = str(uuid.uuid4())
        winner_body = {"data": {"winner": True}}
        IdentitySyncRequestLog.objects.create(
            idempotency_key=key,
            firebase_uid="uid-1",
            method="PUT",
            response_status=201,
            response_body=winner_body,
        )

        # So a PRIMEIRA chamada a .filter() (o check inicial) finge nao ver
        # nada - a busca de recuperacao apos o IntegrityError usa a query
        # real, senao ela tambem cairia na corrida simulada.
        real_filter = IdentitySyncRequestLog.objects.filter
        call_count = {"n": 0}

        def fake_filter(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                empty = Mock()
                empty.first.return_value = None
                return empty
            return real_filter(*args, **kwargs)

        with patch(
            "apps.accounts.internal_views.IdentitySyncRequestLog.objects.filter",
            side_effect=fake_filter,
        ):
            response = self._put("uid-1", _payload(), idempotency_key=key)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), winner_body)

    def test_higher_version_with_changes_updates_and_returns_200(self):
        self._put("uid-1", _payload(version=1))
        response = self._put("uid-1", _payload(role="ADMIN", version=2))
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(firebase_uid="uid-1")
        self.assertEqual(user.role, "ADMIN")
        self.assertEqual(user.identity_version, 2)

    def test_higher_version_without_changes_returns_204(self):
        self._put("uid-1", _payload(version=1))
        response = self._put("uid-1", _payload(version=2))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(response.content)
        self.assertEqual(User.objects.get(firebase_uid="uid-1").identity_version, 2)

    def test_stale_or_equal_version_returns_409(self):
        self._put("uid-1", _payload(version=5))
        response = self._put("uid-1", _payload(version=5))
        self.assertEqual(response.status_code, 409)
        response = self._put("uid-1", _payload(version=3))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.get(firebase_uid="uid-1").identity_version, 5)


@override_settings(INTERNAL_SERVICE_JWT_PUBLIC_KEY=TEST_PUBLIC_KEY)
class IdentitySyncDeleteTests(APITestCase):
    def setUp(self):
        token = _service_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _delete(self, uid, version=1, idempotency_key=None, request_id="req-1"):
        return self.client.delete(
            URL_TMPL.format(uid=uid),
            {"version": version, "occurred_at": "2026-09-03T21:30:00Z"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=idempotency_key or str(uuid.uuid4()),
            HTTP_X_REQUEST_ID=request_id,
        )

    def test_deactivates_active_user_returns_200(self):
        User.objects.create(
            firebase_uid="uid-1", email="a@x.com", role="THERAPIST", active=True
        )
        response = self._delete("uid-1", version=2)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(firebase_uid="uid-1")
        self.assertFalse(user.active)
        self.assertEqual(user.identity_version, 2)

    def test_idempotent_when_already_inactive_returns_204(self):
        User.objects.create(
            firebase_uid="uid-1",
            email="a@x.com",
            role="THERAPIST",
            active=False,
            identity_version=3,
        )
        response = self._delete("uid-1", version=4)
        self.assertEqual(response.status_code, 204)

    def test_unknown_user_returns_204_and_leaves_inactive_tombstone(self):
        response = self._delete("does-not-exist", version=1)
        self.assertEqual(response.status_code, 204)
        user = User.objects.get(firebase_uid="does-not-exist")
        self.assertFalse(user.active)
        self.assertEqual(user.identity_version, 1)

    def test_delete_before_put_prevents_resurrection_by_late_put(self):
        # DELETE v2 chega antes do PUT v1 (fora de ordem, ex: retry/rede).
        self._delete("uid-late", version=2)

        put_token = _service_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {put_token}")
        response = self.client.put(
            URL_TMPL.format(uid="uid-late"),
            _payload(version=1),
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            HTTP_X_REQUEST_ID="req-1",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(User.objects.get(firebase_uid="uid-late").active)

    def test_stale_version_returns_409(self):
        User.objects.create(
            firebase_uid="uid-1",
            email="a@x.com",
            role="THERAPIST",
            active=True,
            identity_version=5,
        )
        response = self._delete("uid-1", version=5)
        self.assertEqual(response.status_code, 409)

    def test_repeated_idempotency_key_does_not_reapply(self):
        User.objects.create(
            firebase_uid="uid-1", email="a@x.com", role="THERAPIST", active=True
        )
        key = str(uuid.uuid4())
        first = self._delete("uid-1", version=2, idempotency_key=key)
        self.assertEqual(first.status_code, 200)
        second = self._delete("uid-1", version=2, idempotency_key=key)
        self.assertEqual(second.status_code, 200)


@override_settings(DEBUG=False)
class FirebaseAuthDeniesUnknownOrInactiveTests(APITestCase):
    """A autenticacao Firebase de usuario final nao deve mais provisionar
    User localmente nem confiar na role do token - so o local User manda."""

    def test_valid_firebase_token_without_local_user_is_denied(self):
        from unittest.mock import patch

        with patch(
            "apps.accounts.authentication.firebase_auth.verify_id_token",
            return_value={"uid": "unknown-uid", "email": "x@x.com"},
        ):
            self.client.credentials(HTTP_AUTHORIZATION="Bearer whatever")
            response = self.client.get("/api/v1/me")
        self.assertEqual(response.status_code, 401)

    def test_valid_firebase_token_for_inactive_local_user_is_denied(self):
        from unittest.mock import patch

        User.objects.create(
            firebase_uid="inactive-uid",
            email="x@x.com",
            role="THERAPIST",
            active=False,
        )
        with patch(
            "apps.accounts.authentication.firebase_auth.verify_id_token",
            return_value={"uid": "inactive-uid", "email": "x@x.com"},
        ):
            self.client.credentials(HTTP_AUTHORIZATION="Bearer whatever")
            response = self.client.get("/api/v1/me")
        self.assertEqual(response.status_code, 401)
