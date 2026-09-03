import uuid

from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.responses import envelope

from .dev_tokens import create_dev_token
from .models import User
from .serializers import UserSerializer, UserUpdateSerializer


class MeView(APIView):
    def get(self, request):
        return Response(envelope(UserSerializer(request.user).data, request))

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

    def post(self, request):
        if not settings.DEBUG:
            raise PermissionDenied("Disponível apenas em DEBUG.")

        role = request.data.get("role", User.THERAPIST)
        if role not in (User.ADMIN, User.THERAPIST):
            return Response({"detail": "role deve ser ADMIN ou THERAPIST"}, status=400)

        uid = request.data.get("uid") or f"dev-{uuid.uuid4().hex[:8]}"
        email = request.data.get("email") or f"{uid}@dev.local"
        token = create_dev_token(uid, email, role)
        return Response({"token": token, "uid": uid, "email": email, "role": role})
