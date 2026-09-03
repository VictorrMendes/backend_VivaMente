from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from config.mixins import resolve_own_professional_or_403

from .models import Appointment

ALLOWED_TRANSITIONS = {
    Appointment.PENDING: {Appointment.CONFIRMED, Appointment.CANCELLED},
    Appointment.CONFIRMED: {Appointment.COMPLETED, Appointment.CANCELLED},
    Appointment.CANCELLED: set(),
    Appointment.COMPLETED: set(),
}


def create_availability_slot(user, serializer):
    if user.role == User.ADMIN:
        serializer.save()
        return
    serializer.save(professional=resolve_own_professional_or_403(user))


def _validate_ownership(professional, client, service):
    if client and client.professional_id != professional.id:
        raise ValidationError({"client": "Cliente não pertence a este profissional."})
    if service and service.professional_id != professional.id:
        raise ValidationError({"service": "Serviço não pertence a este profissional."})


def create_appointment(user, serializer):
    client = serializer.validated_data.get("client")
    service = serializer.validated_data.get("service")

    if user.role == User.ADMIN:
        professional = serializer.validated_data["professional"]
        _validate_ownership(professional, client, service)
        serializer.save()
        return

    professional = resolve_own_professional_or_403(user)
    _validate_ownership(professional, client, service)
    serializer.save(professional=professional)


def update_appointment(serializer):
    instance = serializer.instance
    professional = serializer.validated_data.get("professional", instance.professional)
    client = serializer.validated_data.get("client", instance.client)
    service = serializer.validated_data.get("service", instance.service)
    _validate_ownership(professional, client, service)
    serializer.save()


def transition_status(appointment, new_status):
    if new_status not in ALLOWED_TRANSITIONS.get(appointment.status, set()):
        raise ValidationError(
            {"status": f"Não é possível ir de {appointment.status} para {new_status}."}
        )
    appointment.status = new_status
    appointment.save(update_fields=["status"])
    return appointment
