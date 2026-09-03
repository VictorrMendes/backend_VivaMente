from django.db import models

from apps.professionals.models import Professional


class Service(models.Model):
    ONLINE = "ONLINE"
    IN_PERSON = "IN_PERSON"
    BOTH = "BOTH"
    MODALITY_CHOICES = [(ONLINE, "Online"), (IN_PERSON, "Presencial"), (BOTH, "Ambos")]

    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    modality = models.CharField(max_length=20, choices=MODALITY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "services"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
