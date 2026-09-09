from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.accounts.models import User
from apps.audit.services import log_action
from config.responses import envelope
from config.viewsets import EnvelopeModelViewSet

from . import services
from .models import ClinicalRecord
from .serializers import ClinicalRecordSerializer, ClinicalRecordWriteSerializer


class IsTherapist(BasePermission):
    """Prontuario nunca tem bypass de ADMIN (politica clinica) - diferente
    de todo o resto do sistema, aqui a permissao ja barra o papel inteiro,
    nao so filtra o queryset."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.THERAPIST)


class ClinicalRecordViewSet(EnvelopeModelViewSet):
    permission_classes = [IsTherapist]
    queryset = ClinicalRecord.objects.select_related("client", "professional", "appointment", "author")
    filterset_fields = ["client"]
    ordering_fields = ["recorded_at", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        # Isolamento proprio (nao ProfessionalScopedQuerysetMixin): so o
        # terapeuta responsavel, nunca ADMIN.
        return queryset.filter(professional__user=self.request.user)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ClinicalRecordSerializer
        return ClinicalRecordWriteSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        log_action(request.user, "view", "clinical_record", instance.id, {"client_id": instance.client_id})
        serializer = self.get_serializer(instance)
        return Response(envelope(serializer.data, request))

    def perform_create(self, serializer):
        services.create_clinical_record(self.request.user, serializer)
        log_action(
            self.request.user, "create", "clinical_record", serializer.instance.id,
            {"client_id": serializer.instance.client_id},
        )

    def perform_update(self, serializer):
        services.update_clinical_record(serializer)
        log_action(
            self.request.user, "update", "clinical_record", serializer.instance.id,
            {"client_id": serializer.instance.client_id},
        )

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", "clinical_record", instance.id, {"client_id": instance.client_id})
        instance.delete()
