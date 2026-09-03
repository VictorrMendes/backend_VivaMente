from django.db import models

from apps.accounts.models import User


class Specialty(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        db_table = "specialties"
        verbose_name_plural = "specialties"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Professional(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="professional")
    slug = models.SlugField(max_length=140, unique=True)
    full_name = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    registration = models.CharField(max_length=50, blank=True)
    is_public = models.BooleanField(default=False)
    specialties = models.ManyToManyField(
        Specialty, related_name="professionals", blank=True, db_table="professional_specialties"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "professionals"
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name
