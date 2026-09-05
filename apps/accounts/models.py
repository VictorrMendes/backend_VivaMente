from django.db import models


class User(models.Model):
    ADMIN = "ADMIN"
    THERAPIST = "THERAPIST"
    ROLE_CHOICES = [(ADMIN, "Admin"), (THERAPIST, "Therapist")]

    firebase_uid = models.CharField(max_length=128, unique=True)
    email = models.EmailField()
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=THERAPIST
    )
    active = models.BooleanField(default=True)
    # Versao do ultimo evento de identidade (OAuth) aplicado com sucesso -
    # garante idempotencia/ordenacao dos eventos de sync (ver internal_views.py).
    identity_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    @property
    def is_authenticated(self):
        return True


class IdentitySyncRequestLog(models.Model):
    """Guarda o resultado de cada Idempotency-Key recebido pela API interna
    de sync de identidade, pra devolver a mesma resposta em requests repetidos
    sem reprocessar o evento (ver internal_views.py)."""

    idempotency_key = models.CharField(max_length=100, unique=True)
    firebase_uid = models.CharField(max_length=128)
    method = models.CharField(max_length=10)
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_sync_request_log"
