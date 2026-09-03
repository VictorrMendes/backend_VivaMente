from apps.accounts.models import User
from apps.notifications.models import Notification
from tests.base import AuthenticatedAPITestCase


class NotificationTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.user_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.user_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.notif_a1 = Notification.objects.create(user=self.user_a, title="Novo lead")
        self.notif_a2 = Notification.objects.create(user=self.user_a, title="Agendamento confirmado")
        self.notif_b = Notification.objects.create(user=self.user_b, title="Notificacao de outro user")

    def test_lists_only_own_notifications(self):
        self.login(self.user_a)
        response = self.client.get("/api/v1/notifications")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data), 2)

    def test_requires_authentication(self):
        response = self.client.get("/api/v1/notifications")
        self.assertEqual(response.status_code, 401)

    def test_mark_read(self):
        self.login(self.user_a)
        response = self.client.patch(f"/api/v1/notifications/{self.notif_a1.id}/read")
        self.assertEqual(response.status_code, 200)
        self.notif_a1.refresh_from_db()
        self.assertIsNotNone(self.notif_a1.read_at)

    def test_cannot_mark_others_notification_as_read(self):
        self.login(self.user_a)
        response = self.client.patch(f"/api/v1/notifications/{self.notif_b.id}/read")
        self.assertEqual(response.status_code, 404)
        self.notif_b.refresh_from_db()
        self.assertIsNone(self.notif_b.read_at)

    def test_mark_all_read(self):
        self.login(self.user_a)
        response = self.client.patch("/api/v1/notifications/read-all")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["updated"], 2)
        self.notif_a1.refresh_from_db()
        self.notif_a2.refresh_from_db()
        self.assertIsNotNone(self.notif_a1.read_at)
        self.assertIsNotNone(self.notif_a2.read_at)
        self.notif_b.refresh_from_db()
        self.assertIsNone(self.notif_b.read_at)

    def test_mark_all_read_is_idempotent(self):
        self.login(self.user_a)
        self.client.patch("/api/v1/notifications/read-all")
        response = self.client.patch("/api/v1/notifications/read-all")
        self.assertEqual(response.json()["data"]["updated"], 0)
