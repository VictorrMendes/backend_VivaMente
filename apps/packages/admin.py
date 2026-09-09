from django.contrib import admin

from .models import Package


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "client", "professional", "status", "total_sessions", "start_date"]
    list_filter = ["status"]
