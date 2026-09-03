from rest_framework import serializers

from .models import Client

CLIENT_FIELDS = ["id", "professional", "lead", "name", "email", "phone", "created_at", "updated_at"]


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = CLIENT_FIELDS
        read_only_fields = fields


class ClientWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = CLIENT_FIELDS
        # `lead` so e preenchido pelo fluxo de conversao (POST /leads/{id}/convert)
        read_only_fields = ["id", "lead", "created_at", "updated_at"]


class ClientSelfWriteSerializer(ClientWriteSerializer):
    class Meta(ClientWriteSerializer.Meta):
        read_only_fields = ClientWriteSerializer.Meta.read_only_fields + ["professional"]
