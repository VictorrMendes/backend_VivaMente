from django.db import models


class User(models.Model):
    ADMIN = "ADMIN"
    THERAPIST = "THERAPIST"
    ROLE_CHOICES = [(ADMIN, "Admin"), (THERAPIST, "Therapist")]

    firebase_uid = models.CharField(max_length=128, unique=True)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=THERAPIST)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    @property
    def is_authenticated(self):
        return True
