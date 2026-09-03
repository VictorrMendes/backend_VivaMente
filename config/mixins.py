from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.professionals.models import Professional


def resolve_own_professional_or_403(user):
    """Resolve o Professional do terapeuta autenticado; nega (403) se ele
    ainda nao tiver um perfil profissional. Usado quando um recurso exige
    dono (service, lead, client, appointment...) e quem pede nao e ADMIN,
    entao so pode agir em nome do proprio professional."""
    professional = Professional.objects.filter(user=user).first()
    if professional is None:
        raise PermissionDenied("Você precisa ter um perfil profissional antes de gerenciar este recurso.")
    return professional


class ProfessionalScopedQuerysetMixin:
    """Isola o queryset por terapeuta dono do registro (docs/back.md secao 4).

    O ViewSet define `professional_lookup` com o caminho, a partir do seu
    proprio model, ate o User dono (ex.: "professional__user" quando o model
    referencia um Professional via FK, ou "user" quando o proprio model E
    o Professional).
    """

    professional_lookup = "professional__user"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == User.ADMIN:
            return queryset
        return queryset.filter(**{self.professional_lookup: user})
