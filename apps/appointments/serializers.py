from rest_framework import serializers

from .models import Appointment, AvailabilitySlot


def _validate_period(attrs, instance):
    starts_at = attrs.get("starts_at", getattr(instance, "starts_at", None))
    ends_at = attrs.get("ends_at", getattr(instance, "ends_at", None))
    if starts_at and ends_at and ends_at <= starts_at:
        raise serializers.ValidationError({"ends_at": "Deve ser depois de starts_at."})


AVAILABILITY_FIELDS = ["id", "professional", "starts_at", "ends_at", "is_blocked"]


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = AVAILABILITY_FIELDS
        read_only_fields = fields


class AvailabilitySlotWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = AVAILABILITY_FIELDS
        read_only_fields = ["id"]

    def validate(self, attrs):
        _validate_period(attrs, self.instance)
        return attrs


class AvailabilitySlotSelfWriteSerializer(AvailabilitySlotWriteSerializer):
    class Meta(AvailabilitySlotWriteSerializer.Meta):
        read_only_fields = AvailabilitySlotWriteSerializer.Meta.read_only_fields + ["professional"]


APPOINTMENT_FIELDS = [
    "id",
    "professional",
    "client",
    "service",
    "starts_at",
    "ends_at",
    "status",
    "created_at",
]


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = APPOINTMENT_FIELDS
        read_only_fields = fields


class AppointmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = APPOINTMENT_FIELDS
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, attrs):
        _validate_period(attrs, self.instance)
        return attrs


class AppointmentSelfWriteSerializer(AppointmentWriteSerializer):
    class Meta(AppointmentWriteSerializer.Meta):
        read_only_fields = AppointmentWriteSerializer.Meta.read_only_fields + ["professional"]
