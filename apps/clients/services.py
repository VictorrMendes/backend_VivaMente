from apps.accounts.models import User
from config.mixins import resolve_own_professional_or_403


def create_client(user, serializer):
    if user.role == User.ADMIN:
        serializer.save()
        return
    serializer.save(professional=resolve_own_professional_or_403(user))
