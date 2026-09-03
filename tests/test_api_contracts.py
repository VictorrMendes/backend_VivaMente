from apps.accounts.models import User
from apps.professionals.models import Specialty
from tests.base import AuthenticatedAPITestCase


class ErrorContractTests(AuthenticatedAPITestCase):
    """docs/back.md secao 5: todo erro segue RFC 9457. Isso e um contrato
    usado pela API inteira (config/exceptions.py) e nunca era testado
    diretamente, so incidentalmente via response.status_code nos outros
    testes."""

    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.login(self.admin)

    def test_not_found_error_shape(self):
        response = self.client.get("/api/v1/professionals/999999")
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(
            set(body.keys()), {"type", "title", "status", "detail", "request_id"}
        )
        self.assertEqual(body["status"], 404)
        self.assertEqual(body["title"], "Not Found")
        self.assertTrue(body["type"].endswith("/errors/not-found"))
        self.assertTrue(body["request_id"].startswith("req_"))

    def test_validation_error_shape(self):
        response = self.client.post("/api/v1/specialties", {}, format="json")
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(
            set(body.keys()), {"type", "title", "status", "detail", "request_id"}
        )
        self.assertEqual(body["status"], 400)
        self.assertIn("name", body["detail"])


class PaginationContractTests(AuthenticatedAPITestCase):
    """docs/back.md secao 5: toda listagem responde {data, pagination:
    {page, per_page, total, total_pages}}. Contrato cross-cutting
    (config/pagination.py) nunca testado diretamente."""

    def setUp(self):
        self.admin = User.objects.create(firebase_uid="admin-1", email="admin@teste.com", role=User.ADMIN)
        self.login(self.admin)
        for i in range(3):
            Specialty.objects.create(name=f"Especialidade {i}")

    def test_list_response_has_pagination_shape(self):
        response = self.client.get("/api/v1/specialties")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body.keys()), {"data", "pagination"})
        self.assertEqual(
            set(body["pagination"].keys()), {"page", "per_page", "total", "total_pages"}
        )
        self.assertEqual(body["pagination"]["page"], 1)
        self.assertEqual(body["pagination"]["total"], 3)

    def test_per_page_query_param_limits_page_size(self):
        response = self.client.get("/api/v1/specialties?per_page=2")
        body = response.json()
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["pagination"]["per_page"], 2)
        self.assertEqual(body["pagination"]["total_pages"], 2)
