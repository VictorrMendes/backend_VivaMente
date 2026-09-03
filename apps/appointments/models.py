from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import Func

from apps.clients.models import Client
from apps.professionals.models import Professional
from apps.services.models import Service


class TsTzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class AvailabilitySlot(models.Model):
    professional = models.ForeignKey(
        Professional, on_delete=models.CASCADE, related_name="availability_slots"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_blocked = models.BooleanField(default=False)

    class Meta:
        db_table = "availability_slots"
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["professional", "starts_at"], name="idx_availability_prof_time")
        ]

    def __str__(self):
        return f"{self.professional_id}: {self.starts_at} - {self.ends_at}"


class Appointment(models.Model):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    STATUS_CHOICES = [
        (PENDING, "Pendente"),
        (CONFIRMED, "Confirmado"),
        (CANCELLED, "Cancelado"),
        (COMPLETED, "Concluído"),
    ]

    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="appointments")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="appointments")
    service = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointments"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "appointments"
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["professional", "starts_at"], name="idx_appointments_prof_time")
        ]
        constraints = [
            # Garantia no banco (nao so no serializer/services.py) contra
            # 2 agendamentos sobrepostos do mesmo profissional. Exclui
            # CANCELLED da checagem via `condition`. Precisa da extensao
            # btree_gist (ver migration) pra combinar igualdade de FK com
            # overlap de range no mesmo indice GiST.
            ExclusionConstraint(
                name="exclude_overlapping_appointments",
                expressions=[
                    ("professional", RangeOperators.EQUAL),
                    (TsTzRange("starts_at", "ends_at"), RangeOperators.OVERLAPS),
                ],
                condition=~models.Q(status="CANCELLED"),
            ),
        ]

    def __str__(self):
        return f"{self.client_id} @ {self.starts_at}"
