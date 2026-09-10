from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.payments.models import Payment
from apps.professionals.models import Professional

from .responses import envelope


def _compute_metrics(user):
    if user.role == User.ADMIN:
        leads = Lead.objects.all()
        clients = Client.objects.all()
        appointments = Appointment.objects.all()
        payments = Payment.objects.all()
    else:
        professional = Professional.objects.filter(user=user).first()
        if professional is None:
            raise PermissionDenied("Você precisa ter um perfil profissional antes de ver o dashboard.")
        leads = Lead.objects.filter(professional=professional)
        clients = Client.objects.filter(professional=professional)
        appointments = Appointment.objects.filter(professional=professional)
        payments = Payment.objects.filter(professional=professional)

    now = timezone.now()
    active_appointments = appointments.exclude(status=Appointment.CANCELLED)
    this_month_appointments = active_appointments.filter(starts_at__year=now.year, starts_at__month=now.month)

    upcoming = list(
        active_appointments.filter(starts_at__gte=now)
        .order_by("starts_at")
        .values("id", "client_id", "starts_at", "status")[:5]
    )
    for item in upcoming:
        item["client"] = item.pop("client_id")

    pending_payments = payments.filter(status=Payment.PENDING)
    monthly_paid = payments.filter(status=Payment.PAID, due_date__year=now.year, due_date__month=now.month)

    # Auditoria das proprias acoes do usuario logado - nunca conteudo
    # sensivel, o AuditLog em si nunca guarda isso (ver apps/audit/services.py).
    recent_activity = list(
        AuditLog.objects.filter(user=user)
        .order_by("-created_at")
        .values("action", "resource", "resource_id", "created_at")[:10]
    )

    return {
        "new_leads": leads.filter(status=Lead.NEW).count(),
        "active_clients": clients.count(),
        "sessions_this_month": this_month_appointments.count(),
        "appointments_today": active_appointments.filter(starts_at__date=now.date()).count(),
        "upcoming_appointments": upcoming,
        "pending_payments": {
            "count": pending_payments.count(),
            "total": str(pending_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")),
        },
        "monthly_summary": {
            "received_total": str(monthly_paid.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")),
            "sessions_count": this_month_appointments.count(),
        },
        "recent_activity": recent_activity,
    }


_UPCOMING_APPOINTMENT_FIELDS = {
    "id": serializers.IntegerField(),
    "client": serializers.IntegerField(),
    "starts_at": serializers.DateTimeField(),
    "status": serializers.CharField(),
}

_RECENT_ACTIVITY_FIELDS = {
    "action": serializers.CharField(),
    "resource": serializers.CharField(),
    "resource_id": serializers.CharField(),
    "created_at": serializers.DateTimeField(),
}

_PENDING_PAYMENTS = inline_serializer(
    "PendingPaymentsSummary",
    fields={"count": serializers.IntegerField(), "total": serializers.CharField()},
)

_MONTHLY_SUMMARY = inline_serializer(
    "MonthlySummary",
    fields={"received_total": serializers.CharField(), "sessions_count": serializers.IntegerField()},
)


class DashboardMetricsView(APIView):
    @extend_schema(responses=inline_serializer("DashboardMetrics", fields={
        "new_leads": serializers.IntegerField(),
        "active_clients": serializers.IntegerField(),
        "sessions_this_month": serializers.IntegerField(),
        "appointments_today": serializers.IntegerField(),
        "upcoming_appointments": inline_serializer(
            "UpcomingAppointment", fields=_UPCOMING_APPOINTMENT_FIELDS, many=True
        ),
        "pending_payments": _PENDING_PAYMENTS,
        "monthly_summary": _MONTHLY_SUMMARY,
        "recent_activity": inline_serializer(
            "RecentActivityItem", fields=_RECENT_ACTIVITY_FIELDS, many=True
        ),
    }))
    def get(self, request):
        return Response(envelope(_compute_metrics(request.user), request))
