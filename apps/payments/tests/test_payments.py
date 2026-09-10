from datetime import date

from apps.accounts.models import User
from apps.clients.models import Client
from apps.payments.models import Payment
from apps.professionals.models import Professional
from tests.base import AuthenticatedAPITestCase


class PaymentCRUDTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="B")
        self.client_a = Client.objects.create(professional=self.prof_a, name="Cliente A")
        self.client_b = Client.objects.create(professional=self.prof_b, name="Cliente B")

    def test_therapist_creates_payment_with_generated_receipt(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/payments",
            {"client": self.client_a.id, "amount": "150.00", "due_date": "2026-09-10"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["professional"], self.prof_a.id)
        self.assertEqual(data["status"], "PENDING")
        self.assertTrue(data["receipt_number"].startswith("REC-"))
        self.assertIsNone(data["paid_at"])

    def test_receipt_numbers_are_unique(self):
        self.login(self.therapist_a)
        r1 = self.client.post("/api/v1/payments", {"client": self.client_a.id, "amount": "10"}, format="json")
        r2 = self.client.post("/api/v1/payments", {"client": self.client_a.id, "amount": "20"}, format="json")
        self.assertNotEqual(r1.json()["data"]["receipt_number"], r2.json()["data"]["receipt_number"])

    def test_ignores_client_supplied_receipt_number(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/payments",
            {"client": self.client_a.id, "amount": "10", "receipt_number": "FORJADO-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.json()["data"]["receipt_number"], "FORJADO-1")

    def test_therapist_cannot_create_payment_for_another_therapists_client(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/payments", {"client": self.client_b.id, "amount": "10"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_therapist_lists_only_own_payments(self):
        Payment.objects.create(professional=self.prof_a, client=self.client_a, amount=10, receipt_number="REC-A")
        Payment.objects.create(professional=self.prof_b, client=self.client_b, amount=10, receipt_number="REC-B")
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/payments")
        self.assertEqual(len(response.json()["data"]), 1)

    def test_admin_lists_all_payments(self):
        Payment.objects.create(professional=self.prof_a, client=self.client_a, amount=10, receipt_number="REC-A")
        Payment.objects.create(professional=self.prof_b, client=self.client_b, amount=10, receipt_number="REC-B")
        self.login(self.admin)
        response = self.client.get("/api/v1/payments")
        self.assertEqual(len(response.json()["data"]), 2)

    def test_creating_pending_payment_notifies_professional(self):
        from apps.notifications.models import Notification

        self.login(self.therapist_a)
        self.client.post(
            "/api/v1/payments", {"client": self.client_a.id, "amount": "90.00"}, format="json"
        )
        self.assertTrue(
            Notification.objects.filter(user=self.therapist_a, title="Novo pagamento pendente").exists()
        )

    def test_creating_already_paid_payment_does_not_notify_pending(self):
        from apps.notifications.models import Notification

        self.login(self.therapist_a)
        self.client.post(
            "/api/v1/payments",
            {"client": self.client_a.id, "amount": "90.00", "status": "PAID"},
            format="json",
        )
        self.assertFalse(
            Notification.objects.filter(user=self.therapist_a, title="Novo pagamento pendente").exists()
        )


class PaymentStatusTransitionTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.prof = Professional.objects.create(user=self.therapist, slug="terapeuta-a", full_name="A")
        self.client_obj = Client.objects.create(professional=self.prof, name="Cliente A")
        self.payment = Payment.objects.create(
            professional=self.prof, client=self.client_obj, amount=100, receipt_number="REC-000001"
        )
        self.login(self.therapist)

    def test_marks_as_paid_auto_sets_paid_at(self):
        response = self.client.patch(f"/api/v1/payments/{self.payment.id}", {"status": "PAID"}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "PAID")
        self.assertIsNotNone(data["paid_at"])

    def test_cannot_transition_paid_payment_again(self):
        self.payment.status = Payment.PAID
        self.payment.save(update_fields=["status"])
        response = self.client.patch(f"/api/v1/payments/{self.payment.id}", {"status": "CANCELLED"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cancels_pending_payment(self):
        response = self.client.patch(f"/api/v1/payments/{self.payment.id}", {"status": "CANCELLED"}, format="json")
        self.assertEqual(response.status_code, 200)


class PaymentBalanceTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="B")
        self.client_a = Client.objects.create(professional=self.prof_a, name="Cliente A")
        self.client_b = Client.objects.create(professional=self.prof_b, name="Cliente B")

        Payment.objects.create(
            professional=self.prof_a, client=self.client_a, amount=100, status=Payment.PAID,
            due_date=date(2026, 9, 5), receipt_number="R1",
        )
        Payment.objects.create(
            professional=self.prof_a, client=self.client_a, amount=50, status=Payment.PENDING,
            due_date=date(2026, 9, 20), receipt_number="R2",
        )
        Payment.objects.create(
            professional=self.prof_a, client=self.client_a, amount=999, status=Payment.PAID,
            due_date=date(2026, 8, 1), receipt_number="R3",
        )
        Payment.objects.create(
            professional=self.prof_b, client=self.client_b, amount=500, status=Payment.PAID,
            due_date=date(2026, 9, 5), receipt_number="R4",
        )

    def test_therapist_sees_only_own_scoped_month_balance(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/payments/balance?month=2026-09")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["received_total"], "100.00")
        self.assertEqual(data["received_count"], 1)
        self.assertEqual(data["pending_total"], "50.00")
        self.assertEqual(data["pending_count"], 1)
        self.assertEqual(data["sessions_count"], 2)

    def test_admin_sees_platform_wide_month_balance(self):
        self.login(self.admin)
        response = self.client.get("/api/v1/payments/balance?month=2026-09")
        data = response.json()["data"]
        self.assertEqual(data["received_total"], "600.00")
        self.assertEqual(data["received_count"], 2)

    def test_requires_month_param(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/payments/balance")
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_month_format(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/payments/balance?month=lixo")
        self.assertEqual(response.status_code, 400)

    def test_empty_month_returns_zeroed_totals(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/payments/balance?month=2020-01")
        data = response.json()["data"]
        self.assertEqual(data["received_total"], "0.00")
        self.assertEqual(data["pending_total"], "0.00")
        self.assertEqual(data["sessions_count"], 0)
