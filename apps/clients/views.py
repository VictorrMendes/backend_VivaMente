from apps.accounts.models import User
from config.mixins import ProfessionalScopedQuerysetMixin
from config.viewsets import EnvelopeModelViewSet

from . import services
from .models import Client
from .serializers import ClientSelfWriteSerializer, ClientSerializer, ClientWriteSerializer


class ClientViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    queryset = Client.objects.select_related("professional", "lead")
    filterset_fields = ["professional"]
    ordering_fields = ["name", "created_at"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ClientSerializer
        if self.request.user.role != User.ADMIN:
            return ClientSelfWriteSerializer
        return ClientWriteSerializer

    def perform_create(self, serializer):
        services.create_client(self.request.user, serializer)
