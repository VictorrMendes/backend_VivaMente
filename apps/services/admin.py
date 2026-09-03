from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "professional", "modality", "price", "duration_minutes"]
    list_filter = ["modality"]
    search_fields = ["name"]
