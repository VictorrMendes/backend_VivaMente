from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from config.mixins import resolve_own_professional_or_403

from .models import Payment

ALLOWED_TRANSITIONS = {
    Payment.PENDING: {Payment.PAID, Payment.CANCELLED},
    Payment.PAID: set(),
    Payment.CANCELLED: set(),
}


def _validate_ownership(professional, client, appointment):
    if client.professional_id != professional.id:
        raise ValidationError({"client": "Cliente não pertence a este profissional."})
    if appointment is not None:
        if appointment.professional_id != professional.id:
            raise ValidationError({"appointment": "Agendamento não pertence a este profissional."})
        if appointment.client_id != client.id:
            raise ValidationError({"appointment": "Agendamento não pertence a este cliente."})


def _generate_receipt_number(instance):
    instance.receipt_number = f"REC-{instance.id:06d}"
    instance.save(update_fields=["receipt_number"])


def create_payment(user, serializer):
    client = serializer.validated_data["client"]
    appointment = serializer.validated_data.get("appointment")
    if user.role == User.ADMIN:
        professional = serializer.validated_data["professional"]
    else:
        professional = resolve_own_professional_or_403(user)
    _validate_ownership(professional, client, appointment)

    extra = {"professional": professional}
    if serializer.validated_data.get("status") == Payment.PAID and "paid_at" not in serializer.validated_data:
        extra["paid_at"] = timezone.now()

    with transaction.atomic():
        serializer.save(**extra)
        _generate_receipt_number(serializer.instance)


def update_payment(serializer):
    instance = serializer.instance
    client = serializer.validated_data.get("client", instance.client)
    appointment = serializer.validated_data.get("appointment", instance.appointment)
    _validate_ownership(instance.professional, client, appointment)

    new_status = serializer.validated_data.get("status")
    extra = {}
    if new_status and new_status != instance.status:
        if new_status not in ALLOWED_TRANSITIONS.get(instance.status, set()):
            raise ValidationError({"status": f"Não é possível ir de {instance.status} para {new_status}."})
        if new_status == Payment.PAID and "paid_at" not in serializer.validated_data:
            extra["paid_at"] = timezone.now()

    serializer.save(**extra)
