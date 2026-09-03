from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "id",
            "professional",
            "name",
            "description",
            "duration_minutes",
            "price",
            "modality",
            "created_at",
        ]
        read_only_fields = fields


class ServiceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "id",
            "professional",
            "name",
            "description",
            "duration_minutes",
            "price",
            "modality",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ServiceSelfWriteSerializer(ServiceWriteSerializer):
    """Terapeuta gerencia os proprios servicos; `professional` e sempre o
    dele (definido na view), campo fica visivel na resposta mas read-only."""

    class Meta(ServiceWriteSerializer.Meta):
        read_only_fields = ServiceWriteSerializer.Meta.read_only_fields + ["professional"]
