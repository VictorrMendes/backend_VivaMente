from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.professionals.models import Professional

from .responses import envelope


def _compute_metrics(user):
    if user.role == User.ADMIN:
        leads = Lead.objects.all()
        clients = Client.objects.all()
        appointments = Appointment.objects.all()
    else:
        professional = Professional.objects.filter(user=user).first()
        if professional is None:
            raise PermissionDenied("Você precisa ter um perfil profissional antes de ver o dashboard.")
        leads = Lead.objects.filter(professional=professional)
        clients = Client.objects.filter(professional=professional)
        appointments = Appointment.objects.filter(professional=professional)

    now = timezone.now()
    return {
        "new_leads": leads.filter(status=Lead.NEW).count(),
        "active_clients": clients.count(),
        "sessions_this_month": appointments.filter(starts_at__year=now.year, starts_at__month=now.month)
        .exclude(status=Appointment.CANCELLED)
        .count(),
    }


class DashboardMetricsView(APIView):
    def get(self, request):
        return Response(envelope(_compute_metrics(request.user), request))
