from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.professionals.models import Professional
from config.mixins import ProfessionalScopedQuerysetMixin
from config.viewsets import EnvelopeModelViewSet

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
        user = self.request.user
        if user.role == User.ADMIN:
            serializer.save()
            return
        professional = Professional.objects.filter(user=user).first()
        if professional is None:
            raise PermissionDenied("Você precisa ter um perfil profissional antes de criar clientes.")
        serializer.save(professional=professional)
