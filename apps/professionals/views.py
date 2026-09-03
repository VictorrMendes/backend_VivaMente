from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin
from config.viewsets import EnvelopeModelViewSet

from .models import Professional, Specialty
from .serializers import (
    ProfessionalSelfUpdateSerializer,
    ProfessionalSerializer,
    ProfessionalWriteSerializer,
    SpecialtySerializer,
)


class ProfessionalViewSet(EnvelopeModelViewSet):
    filterset_fields = ["is_public"]
    ordering_fields = ["full_name", "created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.ADMIN:
            return Professional.objects.all()
        return Professional.objects.filter(user=user)

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


class SpecialtyViewSet(EnvelopeModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    ordering_fields = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
