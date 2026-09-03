from apps.accounts.models import User


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
