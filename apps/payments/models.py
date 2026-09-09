from django.db import models

from apps.appointments.models import Appointment
from apps.clients.models import Client
from apps.professionals.models import Professional


class Payment(models.Model):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = [(PENDING, "Pendente"), (PAID, "Pago"), (CANCELLED, "Cancelado")]

    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="payments")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="payments")
    appointment = models.OneToOneField(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="payment"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    # Gerado no servidor (apps/payments/services.py) depois do insert, usando
    # o id auto-increment - nunca aceito do cliente. Fica null na janela
    # entre os 2 saves do create; NULL nao conflita com o unique (ao
    # contrario de ""), entao 2 creates concorrentes nao colidem aqui.
    receipt_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]

    def __str__(self):
        return self.receipt_number or f"Pagamento #{self.pk}"
