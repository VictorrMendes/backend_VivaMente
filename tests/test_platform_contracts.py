from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clients.models import Client
from apps.professionals.models import Professional
from tests.base import AuthenticatedAPITestCase


class PlatformContractTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin", email="admin@example.test", role=User.ADMIN)
        self.therapist = User.objects.create(firebase_uid="owner", email="owner@example.test")
        other = User.objects.create(firebase_uid="other", email="other@example.test")
        self.professional = Professional.objects.create(user=self.therapist, slug="owner", full_name="Owner")
        self.other_professional = Professional.objects.create(user=other, slug="other", full_name="Other")
        self.client_a = Client.objects.create(professional=self.professional, name="A")
        self.client_b = Client.objects.create(professional=self.professional, name="B")
        self.other_client = Client.objects.create(professional=self.other_professional, name="Other")
        now = timezone.now()
        self.first = Appointment.objects.create(
            professional=self.professional, client=self.client_a,
            starts_at=now, ends_at=now + timedelta(minutes=50),
        )
        self.second = Appointment.objects.create(
            professional=self.professional, client=self.client_b, status=Appointment.CONFIRMED,
            starts_at=now + timedelta(hours=2), ends_at=now + timedelta(hours=3),
        )
        self.foreign = Appointment.objects.create(
            professional=self.other_professional, client=self.other_client,
            starts_at=now, ends_at=now + timedelta(minutes=50),
        )
        self.login(self.therapist)

    def test_appointment_filters_use_professional_and_client(self):
        self.login(self.admin)
        for params, expected in [
            ({"professional": self.professional.id}, {self.first.id, self.second.id}),
            ({"client": self.client_a.id}, {self.first.id}),
            ({"professional": self.professional.id, "client": self.client_b.id}, {self.second.id}),
            ({"professional": self.professional.id, "status": "CONFIRMED"}, {self.second.id}),
        ]:
            with self.subTest(params=params):
                response = self.client.get("/api/v1/appointments", params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual({item["id"] for item in response.json()["data"]}, expected)

    def test_filters_cannot_expand_therapist_scope(self):
        for params in [
            {"professional": self.other_professional.id},
            {"client": self.other_client.id},
            {"professional": self.professional.id, "client": self.other_client.id},
        ]:
            with self.subTest(params=params):
                response = self.client.get("/api/v1/appointments", params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["data"], [])
                self.assertEqual(response.json()["pagination"]["total"], 0)

    def test_invalid_filters_return_problem_and_request_id(self):
        for param in ("professional", "client", "status"):
            with self.subTest(param=param):
                response = self.client.get("/api/v1/appointments", {param: "invalid"})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["status"], 400)
                self.assertEqual(response.json()["request_id"], response["X-Request-ID"])

    def test_foreign_appointment_id_is_hidden_for_read_write_and_actions(self):
        path = f"/api/v1/appointments/{self.foreign.id}"
        for method, suffix in [("get", ""), ("patch", ""), ("delete", ""),
                               ("patch", "/confirm"), ("patch", "/cancel"), ("patch", "/complete")]:
            with self.subTest(method=method, suffix=suffix):
                response = getattr(self.client, method)(path + suffix)
                self.assertEqual(response.status_code, 404)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.status, Appointment.PENDING)

    def test_ordering_and_pagination_apply_inside_scope(self):
        response = self.client.get("/api/v1/appointments", {
            "ordering": "starts_at", "page": 2, "per_page": 1,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"data", "pagination"})
        self.assertEqual(response.json()["pagination"], {
            "page": 2, "per_page": 1, "total": 2, "total_pages": 2,
        })
        self.assertEqual(response.json()["data"][0]["id"], self.second.id)
        descending = self.client.get("/api/v1/appointments", {"ordering": "-starts_at"})
        self.assertEqual([row["id"] for row in descending.json()["data"]], [self.second.id, self.first.id])

    def test_me_is_local_user_even_without_professional(self):
        for user in (self.therapist, self.admin):
            with self.subTest(role=user.role):
                self.login(user)
                response = self.client.get("/api/v1/me")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.json()["data"]), {
                    "id", "firebase_uid", "email", "role", "active", "created_at", "updated_at",
                })
                self.assertEqual(response.json()["data"]["id"], user.id)
                self.assertEqual(response.json()["meta"]["request_id"], response["X-Request-ID"])

    def test_me_patch_cannot_change_identity_ownership_or_public_profile(self):
        response = self.client.patch("/api/v1/me", {
            "email": "updated@example.test", "role": "ADMIN", "active": False,
            "firebase_uid": "other", "full_name": "Changed", "bio": "Changed",
            "is_public": True, "professional": self.other_professional.id,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.therapist.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(self.therapist.email, "updated@example.test")
        self.assertEqual(self.therapist.role, User.THERAPIST)
        self.assertTrue(self.therapist.active)
        self.assertEqual(self.therapist.firebase_uid, "owner")
        self.assertEqual(self.professional.full_name, "Owner")
        self.assertEqual(self.professional.bio, "")
        self.assertFalse(self.professional.is_public)

    def test_me_patch_validates_email(self):
        response = self.client.patch("/api/v1/me", {"email": "invalid"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.therapist.refresh_from_db()
        self.assertEqual(self.therapist.email, "owner@example.test")

    def test_access_logs_omit_query_parameters_and_request_body(self):
        with self.assertLogs("api.access", level="INFO") as captured:
            self.client.patch("/api/v1/me?email=query-secret&token=token-secret", {
                "email": "body-secret@example.test",
            }, format="json")
        logs = " ".join(captured.output)
        self.assertIn("PATCH /api/v1/me -> 200", logs)
        for sensitive in ("query-secret", "token-secret", "body-secret"):
            self.assertNotIn(sensitive, logs)

    def test_appointment_response_fields_match_across_operations(self):
        starts_at = timezone.now() + timedelta(days=1)
        created = self.client.post("/api/v1/appointments", {
            "client": self.client_a.id, "professional": self.other_professional.id,
            "starts_at": starts_at.isoformat(), "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["data"]["professional"], self.professional.id)
        path = f"/api/v1/appointments/{created.json()['data']['id']}"
        for response in (created, self.client.get(path), self.client.patch(path, {}, format="json"),
                         self.client.patch(path + "/confirm")):
            with self.subTest(status=response.status_code):
                self.assertIn(response.status_code, (200, 201))
                self.assertEqual(set(response.json()), {"data", "meta"})
                self.assertEqual(set(response.json()["data"]), {
                    "id", "professional", "client", "service", "starts_at", "ends_at", "status", "created_at",
                })
                self.assertEqual(response.json()["meta"]["request_id"], response["X-Request-ID"])
        deleted = self.client.delete(path)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
