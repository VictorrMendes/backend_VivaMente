from rest_framework import serializers

from .models import ClinicalRecord

CLINICAL_RECORD_FIELDS = [
    "id",
    "client",
    "professional",
    "appointment",
    "content",
    "recorded_at",
    "author",
    "created_at",
    "updated_at",
]


class ClinicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalRecord
        fields = CLINICAL_RECORD_FIELDS
        read_only_fields = fields


class ClinicalRecordWriteSerializer(serializers.ModelSerializer):
    """Unico serializer de escrita: quem grava e sempre o proprio terapeuta
    responsavel (nunca ADMIN em nome de outro - ver views.IsTherapist),
    entao nao existe variante self/admin aqui como nos outros apps."""

    class Meta:
        model = ClinicalRecord
        fields = CLINICAL_RECORD_FIELDS
        read_only_fields = ["id", "professional", "author", "created_at", "updated_at"]
