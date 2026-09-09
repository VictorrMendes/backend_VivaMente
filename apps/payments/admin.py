from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "receipt_number", "client", "professional", "amount", "status", "due_date"]
    list_filter = ["status"]
