from django.contrib import admin

from .models import ClinicalRecord


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    """Prontuario e dado sensivel: o admin do Django (superuser) nunca
    exibe/edita `content` aqui, so metadados - ninguem le conteudo clinico
    por essa porta lateral."""

    list_display = ["id", "client", "professional", "appointment", "recorded_at", "author", "created_at"]
    exclude = ["content"]
    readonly_fields = ["client", "professional", "appointment", "author", "recorded_at", "created_at", "updated_at"]
