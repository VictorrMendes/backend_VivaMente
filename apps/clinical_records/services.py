from rest_framework.exceptions import ValidationError

from config.mixins import resolve_own_professional_or_403


def _validate_scope(professional, client, appointment):
    if client.professional_id != professional.id:
        raise ValidationError({"client": "Cliente não pertence a este profissional."})
    if appointment is not None:
        if appointment.professional_id != professional.id:
            raise ValidationError({"appointment": "Agendamento não pertence a este profissional."})
        if appointment.client_id != client.id:
            raise ValidationError({"appointment": "Agendamento não pertence a este cliente."})


def create_clinical_record(user, serializer):
    professional = resolve_own_professional_or_403(user)
    client = serializer.validated_data["client"]
    appointment = serializer.validated_data.get("appointment")
    _validate_scope(professional, client, appointment)
    serializer.save(professional=professional, author=user)


def update_clinical_record(serializer):
    instance = serializer.instance
    client = serializer.validated_data.get("client", instance.client)
    appointment = serializer.validated_data.get("appointment", instance.appointment)
    _validate_scope(instance.professional, client, appointment)
    serializer.save()
