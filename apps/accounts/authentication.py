import os

import firebase_admin
from django.conf import settings
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from .dev_tokens import decode_dev_token
from .models import User


def _get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if cred_path and os.path.exists(cred_path):
        return firebase_admin.initialize_app(credentials.Certificate(cred_path))
    return firebase_admin.initialize_app()


class FirebaseAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.removeprefix("Bearer ")

        claims = decode_dev_token(token) if settings.DEBUG else None
        if claims is None:
            try:
                claims = firebase_auth.verify_id_token(
                    token, app=_get_firebase_app(), check_revoked=True
                )
            except Exception as exc:
                raise exceptions.AuthenticationFailed("Token inválido ou expirado") from exc

        # A role de negocio vem sempre do User local, nunca da claim do
        # Firebase - o Oauth e quem decide/propaga role via API interna
        # (apps.accounts.internal_views), o token do usuario final so prova
        # identidade.
        user = User.objects.filter(firebase_uid=claims["uid"]).first()
        if user is None or not user.active:
            raise exceptions.AuthenticationFailed("Usuário não autorizado.")
        return (user, None)

    def authenticate_header(self, request):
        return "Bearer"
