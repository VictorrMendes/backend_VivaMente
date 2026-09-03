from rest_framework import serializers

from .models import Professional, Specialty


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ["id", "name"]


class ProfessionalSerializer(serializers.ModelSerializer):
    specialties = SpecialtySerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Professional
        fields = [
            "id",
            "user",
            "user_email",
            "slug",
            "full_name",
            "bio",
            "photo_url",
            "registration",
            "is_public",
            "specialties",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_email", "specialties", "created_at", "updated_at"]


class ProfessionalWriteSerializer(serializers.ModelSerializer):
    specialty_ids = serializers.PrimaryKeyRelatedField(
        source="specialties", queryset=Specialty.objects.all(), many=True, required=False
    )

    class Meta:
        model = Professional
        fields = [
            "id",
            "user",
            "slug",
            "full_name",
            "bio",
            "photo_url",
            "registration",
            "is_public",
            "specialty_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProfessionalSelfUpdateSerializer(ProfessionalWriteSerializer):
    """Terapeuta edita o proprio registro, mas nunca troca o `user` dono."""

    class Meta(ProfessionalWriteSerializer.Meta):
        fields = [f for f in ProfessionalWriteSerializer.Meta.fields if f != "user"]
