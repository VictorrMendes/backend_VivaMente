from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.dev_tokens import create_dev_token


@override_settings(DEBUG=True)
class AuthenticatedAPITestCase(APITestCase):
    """Base para testes que autenticam via dev-token (docs/back.md secao 9).
    Centraliza o login pra nao duplicar em cada arquivo de teste, e pra ter
    um unico lugar pra atualizar se o mecanismo de auth mudar."""

    def login(self, user):
        token = create_dev_token(user.firebase_uid, user.email, user.role)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
