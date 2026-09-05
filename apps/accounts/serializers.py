from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "firebase_uid",
            "email",
            "role",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]


class IdentitySyncSerializer(serializers.Serializer):
    """Payload do evento PUT /internal/identity/users/{firebase_uid} enviado
    pelo Oauth. Role e restrita a ADMIN/THERAPIST - o Back nunca aceita um
    papel diferente desses dois pra usuarios locais."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=[User.ADMIN, User.THERAPIST])
    active = serializers.BooleanField()
    version = serializers.IntegerField(min_value=1)
    occurred_at = serializers.DateTimeField()


class IdentitySyncDeleteSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    occurred_at = serializers.DateTimeField()
