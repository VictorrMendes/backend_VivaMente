from rest_framework import serializers

from .models import Package

PACKAGE_FIELDS = [
    "id",
    "professional",
    "client",
    "name",
    "total_sessions",
    "total_value",
    "status",
    "start_date",
    "expiration_date",
    "notes",
    "used_sessions",
    "remaining_sessions",
    "created_at",
    "updated_at",
]


class PackageSerializer(serializers.ModelSerializer):
    used_sessions = serializers.IntegerField(read_only=True)
    remaining_sessions = serializers.IntegerField(read_only=True)

    class Meta:
        model = Package
        fields = PACKAGE_FIELDS
        read_only_fields = fields


class PackageWriteSerializer(serializers.ModelSerializer):
    used_sessions = serializers.IntegerField(read_only=True)
    remaining_sessions = serializers.IntegerField(read_only=True)

    class Meta:
        model = Package
        fields = PACKAGE_FIELDS
        read_only_fields = ["id", "used_sessions", "remaining_sessions", "created_at", "updated_at"]


class PackageSelfWriteSerializer(PackageWriteSerializer):
    class Meta(PackageWriteSerializer.Meta):
        read_only_fields = PackageWriteSerializer.Meta.read_only_fields + ["professional"]
