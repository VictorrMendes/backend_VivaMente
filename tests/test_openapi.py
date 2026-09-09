from io import StringIO

import yaml
from django.core.management import call_command
from django.test import SimpleTestCase


class OpenAPIContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        output, errors = StringIO(), StringIO()
        call_command("spectacular", validate=True, fail_on_warn=True, stdout=output, stderr=errors)
        cls.schema = yaml.safe_load(output.getvalue())
        cls.generation_errors = errors.getvalue()

    def resolve(self, schema):
        while "$ref" in schema:
            schema = self.schema["components"]["schemas"][schema["$ref"].split("/")[-1]]
        return schema

    def response(self, path, method="get", code="200"):
        operation = self.schema["paths"][path][method]
        return self.resolve(operation["responses"][code]["content"]["application/json"]["schema"])

    def test_schema_generation_has_no_warnings_errors_or_database_access(self):
        self.assertEqual(self.generation_errors, "")

    def test_appointment_parameters_match_runtime(self):
        operation = self.schema["paths"]["/api/v1/appointments"]["get"]
        parameters = {p["name"] for p in operation["parameters"] if p["in"] == "query"}
        self.assertEqual(parameters, {"professional", "client", "status", "ordering", "page", "per_page"})

    def test_paginated_resources_document_custom_envelope(self):
        for resource in ("appointments", "availability", "clients", "professionals", "services",
                         "specialties", "leads", "notifications", "audit-logs"):
            with self.subTest(resource=resource):
                schema = self.response(f"/api/v1/{resource}")
                self.assertEqual(set(schema["properties"]), {"data", "pagination"})
                self.assertEqual(schema["properties"]["data"]["type"], "array")
                pagination = schema["properties"]["pagination"]["properties"]
                self.assertEqual(set(pagination), {"page", "per_page", "total", "total_pages"})
                self.assertEqual(pagination["per_page"]["maximum"], 100)

    def test_me_read_and_patch_document_user_envelope_and_only_email_input(self):
        for method in ("get", "patch"):
            response = self.response("/api/v1/me", method)
            self.assertEqual(set(response["properties"]), {"data", "meta"})
            user = self.resolve(response["properties"]["data"])
            self.assertEqual(set(user["properties"]), {
                "id", "firebase_uid", "email", "role", "active", "created_at", "updated_at",
            })
        body = self.schema["paths"]["/api/v1/me"]["patch"]["requestBody"]
        self.assertEqual(set(self.resolve(body["content"]["application/json"]["schema"])["properties"]), {"email"})

    def test_appointment_creation_documents_therapist_input_and_admin_requirement(self):
        operation = self.schema["paths"]["/api/v1/appointments"]["post"]
        body = self.resolve(operation["requestBody"]["content"]["application/json"]["schema"])
        self.assertEqual(set(body["required"]), {"client", "starts_at", "ends_at"})
        self.assertIn("ADMIN", body["properties"]["professional"]["description"])
        self.assertNotIn("status", body["properties"])
        response = self.response("/api/v1/appointments", "post", "201")
        data = self.resolve(response["properties"]["data"])
        self.assertEqual(set(data["properties"]), {
            "id", "professional", "client", "service", "package", "starts_at", "ends_at", "status",
            "modality", "call_link", "price", "notes", "created_at",
        })

    def test_actions_document_actual_results_without_unneeded_input(self):
        for action in ("confirm", "cancel", "complete"):
            path = f"/api/v1/appointments/{{id}}/{action}"
            self.assertNotIn("requestBody", self.schema["paths"][path]["patch"])
            self.assertEqual(self.response(path, "patch")["properties"]["data"]["$ref"],
                             "#/components/schemas/Appointment")
        converted = self.response("/api/v1/leads/{id}/convert", "post", "201")
        self.assertEqual(converted["properties"]["data"]["$ref"], "#/components/schemas/Client")
        read_all = self.response("/api/v1/notifications/read-all", "patch")
        self.assertEqual(set(self.resolve(read_all["properties"]["data"])["properties"]), {"updated"})

    def test_security_schemes_keep_firebase_and_internal_rs256_separate(self):
        self.assertEqual(self.schema["paths"]["/api/v1/me"]["get"]["security"], [{"FirebaseIDToken": []}])
        internal = self.schema["paths"]["/api/v1/internal/identity/users/{firebase_uid}"]
        for method in ("put", "delete"):
            self.assertEqual(internal[method]["security"], [{"IdentitySyncJWT": []}])
            self.assertNotIn("content", internal[method]["responses"]["204"])
            self.assertEqual(self.response("/api/v1/internal/identity/users/{firebase_uid}", method, "409")["type"], "object")
        scheme = self.schema["components"]["securitySchemes"]["IdentitySyncJWT"]
        self.assertEqual(scheme["bearerFormat"], "JWT RS256")

    def test_public_responses_document_only_public_fields(self):
        profile_path = "/api/v1/public/professionals/{slug}"
        self.assertEqual(self.schema["paths"][profile_path]["get"].get("security"), [{}])
        profile = self.resolve(self.response(profile_path)["properties"]["data"])
        self.assertEqual(set(profile["properties"]), {
            "slug", "full_name", "bio", "photo_url", "registration", "specialties", "services",
        })
        public_request = self.response("/api/v1/public/appointment-requests", "post", "201")
        self.assertEqual(set(self.resolve(public_request["properties"]["data"])["properties"]), {"id", "status"})
        slots = self.response(profile_path + "/available-slots")
        self.assertEqual(set(slots["properties"]), {"data", "meta"})
        self.assertEqual(slots["properties"]["data"]["type"], "array")

    def test_problems_headers_and_bodyless_delete(self):
        for code in ("400", "401", "403", "404", "500"):
            self.assertEqual(set(self.response("/api/v1/appointments", code=code)["properties"]),
                             {"type", "title", "status", "detail", "request_id"})
        deleted = self.schema["paths"]["/api/v1/appointments/{id}"]["delete"]["responses"]["204"]
        self.assertNotIn("content", deleted)
        self.assertIn("X-Request-ID", deleted["headers"])

    def test_health_probes_document_unwrapped_responses(self):
        for path in ("health", "health/database", "ready"):
            self.assertEqual(set(self.response(f"/api/v1/{path}")["properties"]), {"status"})
