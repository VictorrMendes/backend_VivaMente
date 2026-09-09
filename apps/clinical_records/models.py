from django.db import models
from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clients.models import Client
from apps.professionals.models import Professional


class ClinicalRecord(models.Model):
    """Prontuario clinico - dado sensivel (docs do projeto, politica clinica).

    Acesso e sempre restrito ao `professional` responsavel; ADMIN nunca tem
    bypass automatico aqui (ver apps/clinical_records/views.py::IsTherapist),
    ao contrario de todo o resto do sistema."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="clinical_records")
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="clinical_records")
    # Unico quando preenchido (OneToOne permite varios NULL); prontuario
    # sem sessao especifica associada (nota avulsa) fica com appointment=None.
    appointment = models.OneToOneField(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="clinical_record"
    )
    content = models.TextField()
    recorded_at = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="authored_clinical_records"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_records"
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["client", "recorded_at"], name="idx_clinrec_client_time")]

    def __str__(self):
        return f"Prontuario #{self.pk} - cliente {self.client_id}"
