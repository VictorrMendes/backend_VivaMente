from rest_framework import serializers

from apps.professionals.models import Professional
from apps.services.models import Service

from .models import Lead

LEAD_FIELDS = [
    "id",
    "professional",
    "name",
    "email",
    "phone",
    "message",
    "service",
    "status",
    "created_at",
    "updated_at",
]


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = LEAD_FIELDS
        read_only_fields = fields


class LeadWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = LEAD_FIELDS
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class LeadSelfWriteSerializer(LeadWriteSerializer):
    """Terapeuta gerencia os proprios leads; `professional` fica read-only (forcado na view)."""

    class Meta(LeadWriteSerializer.Meta):
        read_only_fields = LeadWriteSerializer.Meta.read_only_fields + ["professional"]


class LeadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ["status"]


class PublicAppointmentRequestSerializer(serializers.Serializer):
    professionalSlug = serializers.SlugField()
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    message = serializers.CharField(required=False, allow_blank=True, default="")
    service = serializers.IntegerField(required=False, allow_null=True)
    preferredSlot = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        try:
            professional = Professional.objects.get(slug=attrs["professionalSlug"], is_public=True)
        except Professional.DoesNotExist:
            raise serializers.ValidationError({"professionalSlug": "Profissional não encontrado."})

        service = None
        service_id = attrs.get("service")
        if service_id is not None:
            service = Service.objects.filter(id=service_id, professional=professional).first()
            if service is None:
                raise serializers.ValidationError({"service": "Serviço inválido para este profissional."})

        attrs["professional"] = professional
        attrs["service_obj"] = service
        return attrs

    def create(self, validated_data):
        message = validated_data.get("message", "")
        preferred_slot = validated_data.get("preferredSlot")
        if preferred_slot:
            message = f"Horário solicitado: {preferred_slot.isoformat()}\n{message}".strip()

        return Lead.objects.create(
            professional=validated_data["professional"],
            name=validated_data["name"],
            email=validated_data["email"],
            phone=validated_data.get("phone", ""),
            message=message,
            service=validated_data.get("service_obj"),
        )
