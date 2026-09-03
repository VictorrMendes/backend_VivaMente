from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAdmin
from config.viewsets import EnvelopeRetrieveMixin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(
    EnvelopeRetrieveMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["action", "resource", "user"]
    ordering_fields = ["created_at"]
