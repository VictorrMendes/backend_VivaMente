from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "role", "firebase_uid", "created_at"]
    list_filter = ["role"]
    search_fields = ["email", "firebase_uid"]
