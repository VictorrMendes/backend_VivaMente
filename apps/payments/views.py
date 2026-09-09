from datetime import date
from decimal import Decimal

from django.db.models import Sum
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.models import User
from apps.audit.services import log_action
from config.mixins import ProfessionalScopedQuerysetMixin, resolve_own_professional_or_403
from config.responses import envelope
from config.viewsets import EnvelopeModelViewSet

from . import services
from .models import Payment
from .serializers import PaymentSelfWriteSerializer, PaymentSerializer, PaymentWriteSerializer

_BALANCE_RESPONSE = inline_serializer(
    "PaymentBalance",
    fields={
        "month": serializers.CharField(),
        "received_total": serializers.CharField(),
        "received_count": serializers.IntegerField(),
        "pending_total": serializers.CharField(),
        "pending_count": serializers.IntegerField(),
        "sessions_count": serializers.IntegerField(),
    },
)


class PaymentViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    queryset = Payment.objects.select_related("professional", "client", "appointment")
    filterset_fields = ["client", "status"]
    ordering_fields = ["created_at", "due_date"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve", "balance"):
            return PaymentSerializer
        if getattr(self, "swagger_fake_view", False):
            return PaymentWriteSerializer
        if self.request.user.role != User.ADMIN:
            return PaymentSelfWriteSerializer
        return PaymentWriteSerializer

    def perform_create(self, serializer):
        services.create_payment(self.request.user, serializer)
        log_action(self.request.user, "create", "payment", serializer.instance.id)

    def perform_update(self, serializer):
        services.update_payment(serializer)
        log_action(self.request.user, "update", "payment", serializer.instance.id)

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", "payment", instance.id)
        instance.delete()

    @extend_schema(responses=_BALANCE_RESPONSE)
    @action(detail=False, methods=["get"])
    def balance(self, request):
        month_param = request.query_params.get("month")
        if not month_param:
            raise ValidationError({"month": "Parâmetro obrigatório, formato YYYY-MM."})
        try:
            year_str, month_str = month_param.split("-")
            year, month = int(year_str), int(month_str)
            start = date(year, month, 1)
        except (ValueError, TypeError):
            raise ValidationError({"month": "Formato inválido, use YYYY-MM."})
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        if request.user.role == User.ADMIN:
            queryset = Payment.objects.all()
        else:
            professional = resolve_own_professional_or_403(request.user)
            queryset = Payment.objects.filter(professional=professional)

        month_qs = queryset.filter(due_date__gte=start, due_date__lt=end)
        received = month_qs.filter(status=Payment.PAID)
        pending = month_qs.filter(status=Payment.PENDING)
        received_count = received.count()
        pending_count = pending.count()

        data = {
            "month": month_param,
            "received_total": str(received.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")),
            "received_count": received_count,
            "pending_total": str(pending.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")),
            "pending_count": pending_count,
            "sessions_count": received_count + pending_count,
        }
        return Response(envelope(data, request))
