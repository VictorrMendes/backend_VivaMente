from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.clients.models import Client
from apps.clients.serializers import ClientSerializer
from apps.professionals.models import Professional
from config.mixins import ProfessionalScopedQuerysetMixin
from config.responses import envelope
from config.viewsets import EnvelopeModelViewSet

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
        user = self.request.user
        if user.role == User.ADMIN:
            serializer.save()
            return
        professional = Professional.objects.filter(user=user).first()
        if professional is None:
            raise PermissionDenied("Você precisa ter um perfil profissional antes de criar leads.")
        serializer.save(professional=professional)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadStatusSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(envelope(LeadSerializer(lead).data, request))

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        lead = self.get_object()
        if lead.status == Lead.CONVERTED:
            raise ValidationError({"status": "Lead já foi convertido."})

        client = Client.objects.create(
            professional=lead.professional,
            lead=lead,
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
        )
        lead.status = Lead.CONVERTED
        lead.save(update_fields=["status", "updated_at"])
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
        return Response(envelope(LeadSerializer(lead).data, request), status=201)
