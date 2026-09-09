from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from config.mixins import resolve_own_professional_or_403


def _validate_ownership(professional, client):
    if client.professional_id != professional.id:
        raise ValidationError({"client": "Cliente não pertence a este profissional."})


def create_package(user, serializer):
    client = serializer.validated_data["client"]
    if user.role == User.ADMIN:
        professional = serializer.validated_data["professional"]
    else:
        professional = resolve_own_professional_or_403(user)
    _validate_ownership(professional, client)
    serializer.save(professional=professional)


def update_package(serializer):
    instance = serializer.instance
    client = serializer.validated_data.get("client", instance.client)
    _validate_ownership(instance.professional, client)
    serializer.save()
