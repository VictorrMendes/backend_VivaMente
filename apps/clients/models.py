from django.db import models

from apps.leads.models import Lead
from apps.professionals.models import Professional


class Client(models.Model):
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="clients")
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients")
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clients"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["professional"], name="idx_clients_professional")]

    def __str__(self):
        return self.name
