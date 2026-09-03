from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "action", "resource", "resource_id", "created_at"]
    list_filter = ["action", "resource"]
