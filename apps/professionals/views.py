from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin
from apps.audit.services import log_action
from config.mixins import ProfessionalScopedQuerysetMixin
from config.viewsets import EnvelopeModelViewSet

from .models import Professional, Specialty
from .serializers import (
    ProfessionalSelfUpdateSerializer,
    ProfessionalSerializer,
    ProfessionalWriteSerializer,
    SpecialtySerializer,
)


class ProfessionalViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    professional_lookup = "user"
    queryset = Professional.objects.all()
    filterset_fields = ["is_public"]
    ordering_fields = ["full_name", "created_at"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ProfessionalSerializer
        if self.action in ("update", "partial_update") and self.request.user.role != User.ADMIN:
            return ProfessionalSelfUpdateSerializer
        return ProfessionalWriteSerializer

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()
        log_action(self.request.user, "create", "professional", serializer.instance.id)

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", "professional", instance.id)
        instance.delete()


class SpecialtyViewSet(EnvelopeModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    ordering_fields = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
