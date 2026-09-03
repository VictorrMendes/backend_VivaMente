from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.audit.services import log_action
from apps.clients.serializers import ClientSerializer
from config.mixins import ProfessionalScopedQuerysetMixin
from config.responses import envelope
from config.viewsets import EnvelopeModelViewSet

from . import services
from .models import Lead
from .serializers import (
    LeadSelfWriteSerializer,
    LeadSerializer,
    LeadStatusSerializer,
    LeadWriteSerializer,
    PublicAppointmentRequestSerializer,
)


class LeadViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    queryset = Lead.objects.select_related("professional", "service")
    filterset_fields = ["status", "professional"]
    ordering_fields = ["created_at", "status"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return LeadSerializer
        if self.request.user.role != User.ADMIN:
            return LeadSelfWriteSerializer
        return LeadWriteSerializer

    def perform_create(self, serializer):
        services.create_lead(self.request.user, serializer)
        log_action(self.request.user, "create", "lead", serializer.instance.id)

    def perform_update(self, serializer):
        services.update_lead(serializer)
        log_action(self.request.user, "update", "lead", serializer.instance.id)

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", "lead", instance.id)
        instance.delete()

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadStatusSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, "status_change", "lead", lead.id, {"status": lead.status})
        return Response(envelope(LeadSerializer(lead).data, request))

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        lead = self.get_object()
        client = services.convert_to_client(request.user, lead)
        return Response(envelope(ClientSerializer(client).data, request), status=201)


class PublicAppointmentRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public-appointment-requests"

    def post(self, request):
        serializer = PublicAppointmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        services.notify_professional_of_new_lead(lead)
        # Confirmacao minima: nao ecoa telefone/email/mensagem que o
        # proprio cliente acabou de enviar (achado de auditoria).
        return Response(envelope({"id": lead.id, "status": lead.status}, request), status=201)
