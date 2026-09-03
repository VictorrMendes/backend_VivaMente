from rest_framework import serializers

from apps.professionals.models import Professional, Specialty
from apps.professionals.serializers import SpecialtySerializer
from apps.services.models import Service


class PublicServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price", "modality"]


class PublicProfessionalSerializer(serializers.ModelSerializer):
    """Somente o que pode aparecer na pagina publica /[slug] (docs/back.md secao 7):
    nunca telefone pessoal, agenda interna ou dados de clientes."""

    specialties = SpecialtySerializer(many=True, read_only=True)
    services = PublicServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Professional
        fields = ["slug", "full_name", "bio", "photo_url", "registration", "specialties", "services"]
        read_only_fields = fields


class PublicProfileUpdateSerializer(serializers.ModelSerializer):
    specialty_ids = serializers.PrimaryKeyRelatedField(
        source="specialties", queryset=Specialty.objects.all(), many=True, required=False
    )

    class Meta:
        model = Professional
        fields = ["bio", "photo_url", "registration", "is_public", "specialty_ids"]
