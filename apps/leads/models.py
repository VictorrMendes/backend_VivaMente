from django.db import models

from apps.professionals.models import Professional
from apps.services.models import Service


class Lead(models.Model):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    SCHEDULED = "SCHEDULED"
    CONVERTED = "CONVERTED"
    STATUS_CHOICES = [
        (NEW, "Novo"),
        (CONTACTED, "Contatado"),
        (AWAITING_RESPONSE, "Aguardando resposta"),
        (SCHEDULED, "Agendado"),
        (CONVERTED, "Convertido"),
    ]

    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="leads")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    message = models.TextField(blank=True)
    service = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leads"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["professional", "status"], name="idx_leads_professional_status")]

    def __str__(self):
        return f"{self.name} ({self.status})"
