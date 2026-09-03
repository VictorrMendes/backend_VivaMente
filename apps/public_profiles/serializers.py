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
    services = serializers.SerializerMethodField()

    class Meta:
        model = Professional
        fields = ["slug", "full_name", "bio", "photo_url", "registration", "specialties", "services"]
        read_only_fields = fields

    def get_services(self, obj):
        # ponytail: cap simples em vez de paginacao de verdade pra esse
        # sub-recurso aninhado; se um profissional passar disso, promover
        # pra endpoint proprio GET /public/professionals/{slug}/services
        # com paginacao de listagem normal.
        return PublicServiceSerializer(obj.services.all()[:50], many=True).data


class PublicProfileUpdateSerializer(serializers.ModelSerializer):
    specialty_ids = serializers.PrimaryKeyRelatedField(
        source="specialties", queryset=Specialty.objects.all(), many=True, required=False
    )

    class Meta:
        model = Professional
        fields = ["bio", "photo_url", "registration", "is_public", "specialty_ids"]
