from apps.accounts.models import User
from apps.audit.services import log_action
from config.mixins import ProfessionalScopedQuerysetMixin
from config.viewsets import EnvelopeModelViewSet

from . import services
from .models import Package
from .serializers import PackageSelfWriteSerializer, PackageSerializer, PackageWriteSerializer


class PackageViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    queryset = Package.objects.select_related("professional", "client")
    filterset_fields = ["client", "status"]
    ordering_fields = ["created_at", "start_date"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return PackageSerializer
        if getattr(self, "swagger_fake_view", False):
            return PackageWriteSerializer
        if self.request.user.role != User.ADMIN:
            return PackageSelfWriteSerializer
        return PackageWriteSerializer

    def perform_create(self, serializer):
        services.create_package(self.request.user, serializer)
        log_action(self.request.user, "create", "package", serializer.instance.id)

    def perform_update(self, serializer):
        services.update_package(serializer)
        log_action(self.request.user, "update", "package", serializer.instance.id)

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", "package", instance.id)
        instance.delete()
