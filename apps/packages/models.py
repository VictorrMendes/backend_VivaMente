from django.db import models
from django.utils import timezone

from apps.clients.models import Client
from apps.professionals.models import Professional

# String literal, nao import de apps.appointments.models.Appointment.CANCELLED,
# de proposito: evita ciclo de import (Appointment tera FK pra Package).
_APPOINTMENT_CANCELLED = "CANCELLED"


class Package(models.Model):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = [(ACTIVE, "Ativo"), (COMPLETED, "Concluído"), (CANCELLED, "Cancelado")]

    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="packages")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=200)
    total_sessions = models.PositiveIntegerField()
    total_value = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    start_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "packages"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def used_sessions(self):
        # Computado ao vivo a partir de appointments.package (related_name
        # "appointments"), nunca um contador mutavel duplicado - fonte unica
        # de verdade e a agenda em si.
        return self.appointments.exclude(status=_APPOINTMENT_CANCELLED).count()

    @property
    def remaining_sessions(self):
        return max(self.total_sessions - self.used_sessions, 0)

    def is_expired(self):
        return bool(self.expiration_date and self.expiration_date < timezone.now().date())
