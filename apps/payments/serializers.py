from rest_framework import serializers

from .models import Payment

PAYMENT_FIELDS = [
    "id",
    "professional",
    "client",
    "appointment",
    "amount",
    "status",
    "due_date",
    "paid_at",
    "payment_method",
    "description",
    "receipt_number",
    "created_at",
    "updated_at",
]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = PAYMENT_FIELDS
        read_only_fields = fields


class PaymentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = PAYMENT_FIELDS
        # `paid_at` so muda via transicao de status (services.py), nunca
        # setado direto; `receipt_number` e sempre gerado no servidor.
        read_only_fields = ["id", "paid_at", "receipt_number", "created_at", "updated_at"]


class PaymentSelfWriteSerializer(PaymentWriteSerializer):
    class Meta(PaymentWriteSerializer.Meta):
        read_only_fields = PaymentWriteSerializer.Meta.read_only_fields + ["professional"]
