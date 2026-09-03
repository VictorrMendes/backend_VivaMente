from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from config.mixins import resolve_own_professional_or_403

from .models import Appointment, AvailabilitySlot

OVERLAP_ERROR = {"starts_at": "Já existe um agendamento nesse horário para este profissional."}

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


def _validate_no_overlap(professional, starts_at, ends_at, exclude_id=None):
    conflicts = Appointment.objects.filter(
        professional=professional, starts_at__lt=ends_at, ends_at__gt=starts_at
    ).exclude(status=Appointment.CANCELLED)
    if exclude_id is not None:
        conflicts = conflicts.exclude(id=exclude_id)
    if conflicts.exists():
        raise ValidationError(OVERLAP_ERROR)


def create_appointment(user, serializer):
    client = serializer.validated_data.get("client")
    service = serializer.validated_data.get("service")
    starts_at = serializer.validated_data["starts_at"]
    ends_at = serializer.validated_data["ends_at"]

    if user.role == User.ADMIN:
        professional = serializer.validated_data["professional"]
    else:
        professional = resolve_own_professional_or_403(user)

    _validate_ownership(professional, client, service)
    _validate_no_overlap(professional, starts_at, ends_at)
    try:
        # savepoint proprio: se a constraint do banco rejeitar (corrida que
        # escapou do _validate_no_overlap), so essa escrita e desfeita, nao
        # a transacao inteira do request/teste.
        with transaction.atomic():
            serializer.save(professional=professional)
    except IntegrityError:
        raise ValidationError(OVERLAP_ERROR)


def update_appointment(serializer):
    instance = serializer.instance
    professional = serializer.validated_data.get("professional", instance.professional)
    client = serializer.validated_data.get("client", instance.client)
    service = serializer.validated_data.get("service", instance.service)
    starts_at = serializer.validated_data.get("starts_at", instance.starts_at)
    ends_at = serializer.validated_data.get("ends_at", instance.ends_at)

    _validate_ownership(professional, client, service)
    _validate_no_overlap(professional, starts_at, ends_at, exclude_id=instance.id)
    try:
        with transaction.atomic():
            serializer.save()
    except IntegrityError:
        raise ValidationError(OVERLAP_ERROR)


def list_free_slots(professional):
    """Slots publicos: is_blocked=False E sem nenhum Appointment nao-cancelado
    sobrepondo o horario (achado de auditoria - antes so olhava is_blocked)."""
    conflicting_appointment = Appointment.objects.filter(
        professional=professional,
        starts_at__lt=OuterRef("ends_at"),
        ends_at__gt=OuterRef("starts_at"),
    ).exclude(status=Appointment.CANCELLED)

    return (
        AvailabilitySlot.objects.filter(
            professional=professional, is_blocked=False, starts_at__gte=timezone.now()
        )
        .annotate(has_conflict=Exists(conflicting_appointment))
        .filter(has_conflict=False)
        .order_by("starts_at")
    )


def transition_status(appointment, new_status):
    if new_status not in ALLOWED_TRANSITIONS.get(appointment.status, set()):
        raise ValidationError(
            {"status": f"Não é possível ir de {appointment.status} para {new_status}."}
        )
    appointment.status = new_status
    appointment.save(update_fields=["status"])
    return appointment
