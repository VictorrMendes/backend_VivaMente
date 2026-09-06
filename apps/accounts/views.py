import uuid

from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.responses import envelope

from .dev_tokens import create_dev_token
from .models import User
from .serializers import UserSerializer, UserUpdateSerializer


class MeView(APIView):
    @extend_schema(
        responses=UserSerializer,
        description="Usuario local autenticado. Nao e o perfil profissional nem o perfil publico.",
    )
    def get(self, request):
        return Response(envelope(UserSerializer(request.user).data, request))

    @extend_schema(request=UserUpdateSerializer, responses=UserSerializer,
                   description="Atualiza apenas o email local. Demais campos sao ignorados.")
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(envelope(UserSerializer(request.user).data, request))


class FakeTokenView(APIView):
    """Dev-only backdoor (docs/back.md secao 9): emite um token assinado
    localmente para testar a API sem o servico Oauth/Firebase real.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    envelope_response = False

    @extend_schema(
        description="Somente DEBUG; retorna 403 fora de desenvolvimento. Resposta sem envelope.",
        request=inline_serializer("DevTokenRequest", fields={
            "uid": serializers.CharField(required=False),
            "email": serializers.CharField(required=False),
            "role": serializers.ChoiceField(choices=[User.ADMIN, User.THERAPIST], required=False),
        }),
        responses={200: inline_serializer("DevTokenResponse", fields={
            "token": serializers.CharField(), "uid": serializers.CharField(),
            "email": serializers.CharField(), "role": serializers.CharField(),
        }), 400: inline_serializer("DevTokenError", fields={"detail": serializers.CharField()})},
    )
    def post(self, request):
        if not settings.DEBUG:
            raise PermissionDenied("Disponível apenas em DEBUG.")

        role = request.data.get("role", User.THERAPIST)
        if role not in (User.ADMIN, User.THERAPIST):
            return Response({"detail": "role deve ser ADMIN ou THERAPIST"}, status=400)

        uid = request.data.get("uid") or f"dev-{uuid.uuid4().hex[:8]}"
        email = request.data.get("email") or f"{uid}@dev.local"

        # A autenticacao Firebase real exige o User local ja provisionado
        # (ver authentication.py) - esse backdoor simula o que a API interna
        # de sync (Oauth -> Back) faria antes do usuario logar de verdade.
        User.objects.update_or_create(
            firebase_uid=uid,
            defaults={"email": email, "role": role, "active": True},
        )

        token = create_dev_token(uid, email, role)
        return Response({"token": token, "uid": uid, "email": email, "role": role})
