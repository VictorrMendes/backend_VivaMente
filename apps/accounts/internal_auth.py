import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

SERVICE_ISSUER = "vivamente-oauth"
SERVICE_AUDIENCE = "vivamente-back"
SERVICE_SCOPE = "identity:sync"


class ServicePrincipal:
    """Identidade nao-humana representando o servico Oauth autenticado via
    JWT de servico. Nao e um apps.accounts.models.User (nao tem role de
    negocio) - existe so pra satisfazer request.user nas views internas."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, claims):
        self.claims = claims
        self.scope = claims.get("scope", "")


class ServiceJWTAuthentication(BaseAuthentication):
    """Autentica chamadas machine-to-machine do Oauth via JWT de servico
    assinado com RS256: o Oauth guarda a chave privada e assina, o Back so
    guarda a chave publica e verifica - mesmo que o Back seja comprometido,
    ele nao consegue forjar um token se passando pelo Oauth (diferente de um
    segredo HS256 compartilhado). Nunca aceita Firebase ID Token aqui - essa
    rota e exclusiva para o servico Oauth, nao para usuarios finais."""

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.removeprefix("Bearer ").strip()

        try:
            claims = jwt.decode(
                token,
                settings.INTERNAL_SERVICE_JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                issuer=SERVICE_ISSUER,
                audience=SERVICE_AUDIENCE,
            )
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(
                "Token de servico invalido ou expirado."
            ) from exc

        return (ServicePrincipal(claims), None)

    def authenticate_header(self, request):
        return "Bearer"


class HasIdentitySyncScope(BasePermission):
    def has_permission(self, request, view):
        principal = request.user
        return bool(
            isinstance(principal, ServicePrincipal)
            and SERVICE_SCOPE in principal.scope.split()
        )
