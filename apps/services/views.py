from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.professionals.models import Professional
from config.mixins import ProfessionalScopedQuerysetMixin
from config.viewsets import EnvelopeModelViewSet

from .models import Service
from .serializers import ServiceSelfWriteSerializer, ServiceSerializer, ServiceWriteSerializer


class ServiceViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    queryset = Service.objects.select_related("professional")
    filterset_fields = ["modality", "professional"]
    ordering_fields = ["name", "price", "created_at"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ServiceSerializer
        if self.request.user.role != User.ADMIN:
            return ServiceSelfWriteSerializer
        return ServiceWriteSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == User.ADMIN:
            serializer.save()
            return
        professional = Professional.objects.filter(user=user).first()
        if professional is None:
            raise PermissionDenied("Você precisa ter um perfil profissional antes de criar serviços.")
        serializer.save(professional=professional)
