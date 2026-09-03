from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token
from apps.accounts.models import User
from apps.appointments.models import Appointment, AvailabilitySlot
from apps.clients.models import Client
from apps.professionals.models import Professional
from apps.services.models import Service


@override_settings(DEBUG=True)
class AvailabilitySlotTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="B")

    def _login(self, user):
        token = create_dev_token(user.firebase_uid, user.email, user.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_therapist_creates_own_slot(self):
        self._login(self.therapist_a)
        now = timezone.now()
        response = self.client.post(
            "/api/v1/availability",
            {"starts_at": now.isoformat(), "ends_at": (now + timedelta(hours=1)).isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["professional"], self.prof_a.id)

    def test_rejects_end_before_start(self):
        self._login(self.therapist_a)
        now = timezone.now()
        response = self.client.post(
            "/api/v1/availability",
            {"starts_at": now.isoformat(), "ends_at": (now - timedelta(hours=1)).isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_therapist_lists_only_own_slots(self):
        AvailabilitySlot.objects.create(
            professional=self.prof_a, starts_at=timezone.now(), ends_at=timezone.now() + timedelta(hours=1)
        )
        AvailabilitySlot.objects.create(
            professional=self.prof_b, starts_at=timezone.now(), ends_at=timezone.now() + timedelta(hours=1)
        )
        self._login(self.therapist_a)
        response = self.client.get("/api/v1/availability")
        self.assertEqual(len(response.json()["data"]), 1)


@override_settings(DEBUG=True)
class AppointmentOwnershipTests(APITestCase):
    def setUp(self):
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="B")
        self.client_a = Client.objects.create(professional=self.prof_a, name="Cliente A")
        self.client_b = Client.objects.create(professional=self.prof_b, name="Cliente B")
        self.now = timezone.now()

    def _login(self, user):
        token = create_dev_token(user.firebase_uid, user.email, user.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _payload(self, client_id):
        return {
            "client": client_id,
            "starts_at": self.now.isoformat(),
            "ends_at": (self.now + timedelta(minutes=50)).isoformat(),
        }

    def test_therapist_creates_appointment_for_own_client(self):
        self._login(self.therapist_a)
        response = self.client.post("/api/v1/appointments", self._payload(self.client_a.id), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["professional"], self.prof_a.id)
        self.assertEqual(response.json()["data"]["status"], "PENDING")

    def test_therapist_cannot_book_another_professionals_client(self):
        self._login(self.therapist_a)
        response = self.client.post("/api/v1/appointments", self._payload(self.client_b.id), format="json")
        self.assertEqual(response.status_code, 400)

    def test_therapist_lists_only_own_appointments(self):
        Appointment.objects.create(
            professional=self.prof_a, client=self.client_a, starts_at=self.now, ends_at=self.now + timedelta(hours=1)
        )
        Appointment.objects.create(
            professional=self.prof_b, client=self.client_b, starts_at=self.now, ends_at=self.now + timedelta(hours=1)
        )
        self._login(self.therapist_a)
        response = self.client.get("/api/v1/appointments")
        self.assertEqual(len(response.json()["data"]), 1)


@override_settings(DEBUG=True)
class AppointmentTransitionTests(APITestCase):
    def setUp(self):
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.prof = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        self.client_obj = Client.objects.create(professional=self.prof, name="Cliente A")
        now = timezone.now()
        self.appointment = Appointment.objects.create(
            professional=self.prof, client=self.client_obj, starts_at=now, ends_at=now + timedelta(hours=1)
        )
        token = create_dev_token(self.therapist.firebase_uid, self.therapist.email, self.therapist.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_confirm_then_complete(self):
        response = self.client.patch(f"/api/v1/appointments/{self.appointment.id}/confirm")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "CONFIRMED")

        response = self.client.patch(f"/api/v1/appointments/{self.appointment.id}/complete")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "COMPLETED")

    def test_cannot_complete_without_confirming(self):
        response = self.client.patch(f"/api/v1/appointments/{self.appointment.id}/complete")
        self.assertEqual(response.status_code, 400)

    def test_cannot_transition_after_cancelled(self):
        self.client.patch(f"/api/v1/appointments/{self.appointment.id}/cancel")
        response = self.client.patch(f"/api/v1/appointments/{self.appointment.id}/confirm")
        self.assertEqual(response.status_code, 400)


@override_settings(DEBUG=True)
class PublicAvailableSlotsTests(APITestCase):
    def setUp(self):
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.prof = Professional.objects.create(
            user=self.therapist, slug="terapeuta-publica", full_name="A", is_public=True
        )
        now = timezone.now()
        self.free_slot = AvailabilitySlot.objects.create(
            professional=self.prof, starts_at=now + timedelta(days=1), ends_at=now + timedelta(days=1, hours=1)
        )
        AvailabilitySlot.objects.create(
            professional=self.prof,
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=2, hours=1),
            is_blocked=True,
        )

    def test_returns_only_free_slots_without_auth(self):
        response = self.client.get("/api/v1/public/professionals/terapeuta-publica/available-slots")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.free_slot.id)

    def test_404_for_unknown_slug(self):
        response = self.client.get("/api/v1/public/professionals/nao-existe/available-slots")
        self.assertEqual(response.status_code, 404)
