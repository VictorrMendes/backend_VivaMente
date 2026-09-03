from apps.accounts.models import User
from apps.audit.services import log_action
from config.mixins import ProfessionalScopedQuerysetMixin
from config.viewsets import EnvelopeModelViewSet

from . import services
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
        services.create_service(self.request.user, serializer)
        log_action(self.request.user, "create", "service", serializer.instance.id)

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", "service", instance.id)
        instance.delete()
