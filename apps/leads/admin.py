from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "professional", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "email"]
