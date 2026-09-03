from django.contrib import admin

from .models import Appointment, AvailabilitySlot


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ["id", "professional", "starts_at", "ends_at", "is_blocked"]
    list_filter = ["is_blocked"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["id", "professional", "client", "starts_at", "status"]
    list_filter = ["status"]
