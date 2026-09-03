from apps.accounts.models import User
from apps.professionals.models import Professional, Specialty
from tests.base import AuthenticatedAPITestCase


class ProfessionalIsolationTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist_a = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.therapist_b = User.objects.create(firebase_uid="ther-b", email="b@teste.com", role=User.THERAPIST)
        self.prof_a = Professional.objects.create(user=self.therapist_a, slug="terapeuta-a", full_name="Terapeuta A")
        self.prof_b = Professional.objects.create(user=self.therapist_b, slug="terapeuta-b", full_name="Terapeuta B")

    def test_therapist_lists_only_own_professional(self):
        self.login(self.therapist_a)
        response = self.client.get("/api/v1/professionals")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["slug"], "terapeuta-a")

    def test_admin_lists_all_professionals(self):
        self.login(self.admin)
        response = self.client.get("/api/v1/professionals")
        self.assertEqual(len(response.json()["data"]), 2)

    def test_therapist_cannot_read_other_professional_gets_404(self):
        self.login(self.therapist_a)
        response = self.client.get(f"/api/v1/professionals/{self.prof_b.id}")
        self.assertEqual(response.status_code, 404)

    def test_therapist_cannot_create_professional(self):
        self.login(self.therapist_a)
        response = self.client.post(
            "/api/v1/professionals", {"user": self.therapist_b.id, "slug": "x", "full_name": "X"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_professional(self):
        new_user = User.objects.create(firebase_uid="ther-c", email="c@teste.com", role=User.THERAPIST)
        self.login(self.admin)
        response = self.client.post(
            "/api/v1/professionals",
            {"user": new_user.id, "slug": "terapeuta-c", "full_name": "Terapeuta C"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.json()["data"])

    def test_therapist_can_update_own_professional(self):
        self.login(self.therapist_a)
        response = self.client.patch(
            f"/api/v1/professionals/{self.prof_a.id}", {"bio": "Nova bio"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.prof_a.refresh_from_db()
        self.assertEqual(self.prof_a.bio, "Nova bio")

    def test_therapist_cannot_reassign_professional_owner(self):
        self.login(self.therapist_a)
        response = self.client.patch(
            f"/api/v1/professionals/{self.prof_a.id}", {"user": self.therapist_b.id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.prof_a.refresh_from_db()
        self.assertEqual(self.prof_a.user_id, self.therapist_a.id)

    def test_therapist_cannot_delete_professional(self):
        self.login(self.therapist_a)
        response = self.client.delete(f"/api/v1/professionals/{self.prof_a.id}")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_delete_professional(self):
        self.login(self.admin)
        response = self.client.delete(f"/api/v1/professionals/{self.prof_a.id}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Professional.objects.filter(id=self.prof_a.id).exists())


class SpecialtyRBACTests(AuthenticatedAPITestCase):
    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.therapist = User.objects.create(firebase_uid="ther-a", email="a@teste.com", role=User.THERAPIST)
        self.specialty = Specialty.objects.create(name="Ansiedade")

    def test_therapist_can_read_specialties(self):
        self.login(self.therapist)
        response = self.client.get("/api/v1/specialties")
        self.assertEqual(response.status_code, 200)

    def test_therapist_cannot_create_specialty(self):
        self.login(self.therapist)
        response = self.client.post("/api/v1/specialties", {"name": "Depressão"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_specialty(self):
        self.login(self.admin)
        response = self.client.post("/api/v1/specialties", {"name": "Depressão"}, format="json")
        self.assertEqual(response.status_code, 201)
