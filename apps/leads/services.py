from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.audit.services import log_action
from apps.clients.models import Client
from apps.notifications.models import Notification
from config.mixins import resolve_own_professional_or_403

from .models import Lead


def _validate_service_ownership(professional, service):
    if service and service.professional_id != professional.id:
        raise ValidationError({"service": "Serviço não pertence a este profissional."})


def create_lead(user, serializer):
    service = serializer.validated_data.get("service")
    if user.role == User.ADMIN:
        professional = serializer.validated_data["professional"]
    else:
        professional = resolve_own_professional_or_403(user)
    _validate_service_ownership(professional, service)
    serializer.save(professional=professional)


def update_lead(serializer):
    instance = serializer.instance
    service = serializer.validated_data.get("service", instance.service)
    _validate_service_ownership(instance.professional, service)
    serializer.save()


def convert_to_client(user, lead):
    with transaction.atomic():
        # select_for_update trava a linha: se duas requests chamarem
        # convert() pro mesmo lead ao mesmo tempo, a segunda espera a
        # primeira commitar e ve o status ja CONVERTED, sem criar 2 clients.
        locked_lead = Lead.objects.select_for_update().get(pk=lead.pk)
        if locked_lead.status == Lead.CONVERTED:
            raise ValidationError({"status": "Lead já foi convertido."})

        client = Client.objects.create(
            professional=locked_lead.professional,
            lead=locked_lead,
            name=locked_lead.name,
            email=locked_lead.email,
            phone=locked_lead.phone,
        )
        locked_lead.status = Lead.CONVERTED
        locked_lead.save(update_fields=["status", "updated_at"])

    log_action(user, "convert", "lead", locked_lead.id, {"client_id": client.id})
    return client


def notify_professional_of_new_lead(lead):
    Notification.objects.create(
        user=lead.professional.user,
        title="Novo lead recebido",
        body=f"{lead.name} entrou em contato.",
    )
