from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.audit.services import log_action
from apps.clients.models import Client
from config.mixins import resolve_own_professional_or_403

from .models import Lead


def create_lead(user, serializer):
    if user.role == User.ADMIN:
        serializer.save()
        return
    serializer.save(professional=resolve_own_professional_or_403(user))


def convert_to_client(user, lead):
    if lead.status == Lead.CONVERTED:
        raise ValidationError({"status": "Lead já foi convertido."})

    client = Client.objects.create(
        professional=lead.professional,
        lead=lead,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
    )
    lead.status = Lead.CONVERTED
    lead.save(update_fields=["status", "updated_at"])
    log_action(user, "convert", "lead", lead.id, {"client_id": client.id})
    return client
