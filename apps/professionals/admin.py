from django.contrib import admin

from .models import Professional, Specialty


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ["id", "full_name", "slug", "user", "is_public", "created_at"]
    list_filter = ["is_public"]
    search_fields = ["full_name", "slug"]
