from datetime import date, timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clients.models import Client
from apps.packages.models import Package
from apps.professionals.models import Professional
from tests.base import AuthenticatedAPITestCase


class PackageCRUDTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="B")
        self.client_a = Client.objects.create(professional=self.prof_a, name="Cliente A")
        self.client_b = Client.objects.create(professional=self.prof_b, name="Cliente B")

    def test_therapist_creates_package_for_own_client(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/packages",
            {
                "client": self.client_a.id,
                "name": "Pacote 10 sessões",
                "total_sessions": 10,
                "total_value": "1500.00",
                "start_date": "2026-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["professional"], self.prof_a.id)
        self.assertEqual(data["used_sessions"], 0)
        self.assertEqual(data["remaining_sessions"], 10)

    def test_therapist_cannot_create_package_for_another_therapists_client(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/packages",
            {"client": self.client_b.id, "name": "X", "total_sessions": 1, "total_value": "1", "start_date": "2026-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_therapist_lists_only_own_packages(self):
        Package.objects.create(
            professional=self.prof_a, client=self.client_a, name="A", total_sessions=1, total_value=1,
            start_date=date.today(),
        )
        Package.objects.create(
            professional=self.prof_b, client=self.client_b, name="B", total_sessions=1, total_value=1,
            start_date=date.today(),
        )
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/packages")
        self.assertEqual(len(response.json()["data"]), 1)

    def test_admin_lists_all_packages(self):
        Package.objects.create(
            professional=self.prof_a, client=self.client_a, name="A", total_sessions=1, total_value=1,
            start_date=date.today(),
        )
        Package.objects.create(
            professional=self.prof_b, client=self.client_b, name="B", total_sessions=1, total_value=1,
            start_date=date.today(),
        )
        self.login(self.admin)
        response = self.client.get("/api/v1/packages")
        self.assertEqual(len(response.json()["data"]), 2)


class PackageBalanceTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.prof = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        self.client_obj = Client.objects.create(professional=self.prof, name="Cliente A")
        self.package = Package.objects.create(
            professional=self.prof, client=self.client_obj, name="Pacote", total_sessions=2,
            total_value=200, start_date=date.today(),
        )
        self.now = timezone.now()
        self.login(self.therapist)

    def _book(self, offset_days, **extra):
        starts_at = self.now + timedelta(days=offset_days)
        return self.client.post(
            "/api/v1/appointments",
            {
                "client": self.client_obj.id,
                "package": self.package.id,
                "starts_at": starts_at.isoformat(),
                "ends_at": (starts_at + timedelta(minutes=50)).isoformat(),
                **extra,
            },
            format="json",
        )

    def test_used_and_remaining_reflect_non_cancelled_appointments(self):
        response = self._book(1)
        self.assertEqual(response.status_code, 201)
        appointment_id = response.json()["data"]["id"]

        cancelled = self._book(2)
        self.assertEqual(cancelled.status_code, 201)
        self.client.patch(f"/api/v1/appointments/{cancelled.json()['data']['id']}/cancel")

        data = self.client.get(f"/api/v1/packages/{self.package.id}").json()["data"]
        self.assertEqual(data["used_sessions"], 1)
        self.assertEqual(data["remaining_sessions"], 1)
        self.assertTrue(Appointment.objects.filter(id=appointment_id, package=self.package).exists())

    def test_blocks_booking_when_no_balance_left(self):
        self._book(1)
        self._book(2)
        response = self._book(3)
        self.assertEqual(response.status_code, 400)
        self.assertIn("package", response.json()["detail"])

    def test_blocks_booking_on_cancelled_package(self):
        self.package.status = Package.CANCELLED
        self.package.save(update_fields=["status"])
        response = self._book(1)
        self.assertEqual(response.status_code, 400)

    def test_blocks_booking_on_completed_package(self):
        self.package.status = Package.COMPLETED
        self.package.save(update_fields=["status"])
        response = self._book(1)
        self.assertEqual(response.status_code, 400)

    def test_blocks_booking_on_expired_package(self):
        self.package.expiration_date = date.today() - timedelta(days=1)
        self.package.save(update_fields=["expiration_date"])
        response = self._book(1)
        self.assertEqual(response.status_code, 400)

    def test_blocks_package_from_another_client(self):
        other_client = Client.objects.create(professional=self.prof, name="Outro Cliente")
        response = self.client.post(
            "/api/v1/appointments",
            {
                "client": other_client.id,
                "package": self.package.id,
                "starts_at": self.now.isoformat(),
                "ends_at": (self.now + timedelta(minutes=50)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unrelated_update_does_not_revalidate_existing_package_link(self):
        response = self._book(1)
        appointment_id = response.json()["data"]["id"]
        self._book(2)
        # pacote agora sem saldo - mas so editar `notes` nao deve reavaliar o
        # vinculo ja existente com o pacote.
        patch = self.client.patch(f"/api/v1/appointments/{appointment_id}", {"notes": "Nota"}, format="json")
        self.assertEqual(patch.status_code, 200)
