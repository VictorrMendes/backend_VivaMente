from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "professional", "lead", "created_at"]
    search_fields = ["name", "email"]
