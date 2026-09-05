from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from config.responses import envelope

from .internal_auth import HasIdentitySyncScope, ServiceJWTAuthentication
from .models import IdentitySyncRequestLog, User
from .serializers import (
    IdentitySyncDeleteSerializer,
    IdentitySyncSerializer,
    UserSerializer,
)

_INTERNAL_HEADERS = [
    OpenApiParameter(
        name="Idempotency-Key",
        location=OpenApiParameter.HEADER,
        required=True,
        type=str,
        description="UUID unico do evento, usado para ignorar repeticoes.",
    ),
    OpenApiParameter(
        name="X-Request-Id",
        location=OpenApiParameter.HEADER,
        required=True,
        type=str,
        description="Request id propagado pelo Oauth para correlacao de logs.",
    ),
]


class VersionConflict(exceptions.APIException):
    status_code = 409
    default_detail = "Evento de identidade desatualizado (version <= aplicada)."
    default_code = "conflict"


def _require_headers(request):
    idempotency_key = request.headers.get("Idempotency-Key")
    request_id = request.headers.get("X-Request-Id")
    if not idempotency_key:
        raise exceptions.ValidationError("Header Idempotency-Key e obrigatorio.")
    if not request_id:
        raise exceptions.ValidationError("Header X-Request-Id e obrigatorio.")
    return idempotency_key, request_id


def _cached_response_or_raise(idempotency_key):
    """Duas requests com a MESMA Idempotency-Key podem passar pelo check de
    cache antes de qualquer uma commitar (race). A unique constraint em
    IdentitySyncRequestLog.idempotency_key pega isso na gravacao final -
    aqui so buscamos a resposta que a vencedora da corrida gravou."""
    cached = IdentitySyncRequestLog.objects.filter(
        idempotency_key=idempotency_key
    ).first()
    if cached is not None:
        return Response(cached.response_body, status=cached.response_status)
    raise


class IdentityUserSyncView(APIView):
    """API interna, m2m-only, usada pelo Oauth pra manter o User local do
    Back em sincronia com a identidade (Firebase). Nunca e chamada por um
    frontend nem aceita Firebase ID Token - apenas o JWT de servico do Oauth
    (ver internal_auth.py). Deve ficar restrita a rede privada no Traefik
    quando essa infraestrutura existir.
    """

    authentication_classes = [ServiceJWTAuthentication]
    permission_classes = [HasIdentitySyncScope]

    @extend_schema(
        tags=["internal-identity-sync"],
        parameters=_INTERNAL_HEADERS,
        request=IdentitySyncSerializer,
        responses={
            201: UserSerializer,
            200: UserSerializer,
            204: None,
            409: None,
        },
        description=(
            "Uso exclusivo do servico Oauth (JWT de servico, "
            "scope identity:sync). Cria ou atualiza o User local "
            "pelo firebase_uid de forma idempotente e ordenada por version."
        ),
    )
    def put(self, request, firebase_uid):
        idempotency_key, request_id = _require_headers(request)

        cached = IdentitySyncRequestLog.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        if cached is not None:
            return Response(cached.response_body, status=cached.response_status)

        serializer = IdentitySyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().filter(
                    firebase_uid=firebase_uid
                ).first()

                if user is None:
                    user = User.objects.create(
                        firebase_uid=firebase_uid,
                        email=data["email"],
                        role=data["role"],
                        active=data["active"],
                        identity_version=data["version"],
                    )
                    status_code = 201
                elif data["version"] <= user.identity_version:
                    raise VersionConflict()
                else:
                    changed = (
                        user.email != data["email"]
                        or user.role != data["role"]
                        or user.active != data["active"]
                    )
                    user.identity_version = data["version"]
                    if changed:
                        user.email = data["email"]
                        user.role = data["role"]
                        user.active = data["active"]
                        user.save(
                            update_fields=[
                                "email", "role", "active", "identity_version"
                            ]
                        )
                        status_code = 200
                    else:
                        user.save(update_fields=["identity_version"])
                        status_code = 204

                body = (
                    envelope(UserSerializer(user).data, request)
                    if status_code != 204
                    else None
                )

                log_action(
                    user,
                    "identity_sync_put",
                    "user",
                    user.id,
                    metadata={
                        "role": data["role"],
                        "active": data["active"],
                        "version": data["version"],
                        "request_id": request_id,
                    },
                )

                IdentitySyncRequestLog.objects.create(
                    idempotency_key=idempotency_key,
                    firebase_uid=firebase_uid,
                    method="PUT",
                    response_status=status_code,
                    response_body=body,
                )
        except IntegrityError:
            return _cached_response_or_raise(idempotency_key)

        return Response(body, status=status_code)

    @extend_schema(
        tags=["internal-identity-sync"],
        parameters=_INTERNAL_HEADERS,
        request=IdentitySyncDeleteSerializer,
        responses={200: None, 204: None, 409: None},
        description=(
            "Uso exclusivo do servico Oauth. Desativa o User local "
            "(nunca apaga fisicamente) de forma idempotente."
        ),
    )
    def delete(self, request, firebase_uid):
        idempotency_key, request_id = _require_headers(request)

        cached = IdentitySyncRequestLog.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        if cached is not None:
            return Response(cached.response_body, status=cached.response_status)

        serializer = IdentitySyncDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().filter(
                    firebase_uid=firebase_uid
                ).first()

                if user is None:
                    # Tombstone: nunca existiu localmente, mas registramos a
                    # version mesmo assim - sem isso, um PUT atrasado (fora
                    # de ordem) com version menor chegaria depois e
                    # ressuscitaria um usuario que o Oauth ja deletou.
                    user = User.objects.create(
                        firebase_uid=firebase_uid,
                        email="",
                        role=User.THERAPIST,
                        active=False,
                        identity_version=data["version"],
                    )
                    status_code = 204
                elif data["version"] <= user.identity_version:
                    raise VersionConflict()
                elif not user.active:
                    user.identity_version = data["version"]
                    user.save(update_fields=["identity_version"])
                    status_code = 204
                else:
                    user.active = False
                    user.identity_version = data["version"]
                    user.save(update_fields=["active", "identity_version"])
                    status_code = 200

                log_action(
                    user,
                    "identity_sync_delete",
                    "user",
                    user.id,
                    metadata={"version": data["version"], "request_id": request_id},
                )

                IdentitySyncRequestLog.objects.create(
                    idempotency_key=idempotency_key,
                    firebase_uid=firebase_uid,
                    method="DELETE",
                    response_status=status_code,
                    response_body=None,
                )
        except IntegrityError:
            return _cached_response_or_raise(idempotency_key)

        return Response(status=status_code)
