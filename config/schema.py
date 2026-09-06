"""OpenAPI dos envelopes existentes; nao altera respostas em runtime."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from rest_framework import serializers


class FirebaseAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.FirebaseAuthentication"
    name = "FirebaseIDToken"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "Firebase ID Token"}


class ServiceJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.internal_auth.ServiceJWTAuthentication"
    name = "IdentitySyncJWT"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http", "scheme": "bearer", "bearerFormat": "JWT RS256",
            "description": "Exclusivo do OAuth, scope identity:sync. Nao aceita Firebase ID Token.",
        }


class ProblemSerializer(serializers.Serializer):
    type = serializers.URLField()
    title = serializers.CharField()
    status = serializers.IntegerField()
    detail = serializers.CharField()
    request_id = serializers.CharField()


def add_health_paths(result, generator, request, public):
    """Probes Django (JsonResponse), fora da introspeccao de views DRF."""
    for suffix, value in (("health", "ok"), ("health/database", "ok"), ("ready", "ready")):
        result["paths"][f"/api/v1/{suffix}"] = {"get": {
            "operationId": "v1_" + suffix.replace("/", "_") + "_retrieve",
            "tags": ["health"], "security": [],
            "responses": {"200": {
                "description": "Probe sem envelope.",
                "headers": {"X-Request-ID": {"schema": {"type": "string"}}},
                "content": {"application/json": {"schema": {
                    "type": "object", "required": ["status"],
                    "properties": {"status": {"type": "string", "enum": [value]}},
                }}},
            }},
        }}
    return result


class EnvelopeSchema(AutoSchema):
    def get_request_serializer(self):
        serializer = super().get_request_serializer()
        if isinstance(serializer, serializers.ModelSerializer):
            owner = serializer.fields.get("professional")
            if owner is not None and not owner.read_only:
                owner.required = False
                owner.help_text = (
                    "ADMIN deve informar na criacao. Para THERAPIST, ignorado e definido "
                    "pelo usuario autenticado; nao permite transferir o recurso."
                )
        return serializer

    def _get_response_bodies(self, direction="response"):
        responses = super()._get_response_bodies(direction)
        for code in ("400", "401", "403", "404", "405", "500"):
            responses.setdefault(code, self._get_response_for_code(ProblemSerializer, code))
        if self.view.throttle_classes:
            responses.setdefault("429", self._get_response_for_code(ProblemSerializer, "429"))
        for code, response in responses.items():
            response.setdefault("headers", {})["X-Request-ID"] = {
                "schema": {"type": "string"}, "description": "Identificador da requisicao.",
            }
            if not code.startswith("2") or not getattr(self.view, "envelope_response", True):
                continue
            # ListModelMixin usa DefaultPagination, que descreve seu proprio envelope.
            if getattr(self.view, "action", None) == "list" and self._get_paginator():
                continue
            for media in response.get("content", {}).values():
                media["schema"] = {
                    "type": "object", "required": ["data", "meta"],
                    "properties": {
                        "data": media["schema"],
                        "meta": {
                            "type": "object", "required": ["request_id", "timestamp"],
                            "properties": {
                                "request_id": {"type": "string"},
                                "timestamp": {"type": "string", "format": "date-time"},
                            },
                        },
                    },
                }
        return responses
