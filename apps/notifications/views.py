from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.responses import envelope

from . import services
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    filterset_fields = ["read_at"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        services.mark_read(notification)
        return Response(envelope(NotificationSerializer(notification).data, request))

    @action(detail=False, methods=["patch"], url_path="read-all")
    def mark_all_read(self, request):
        updated = services.mark_all_read(self.get_queryset())
        return Response(envelope({"updated": updated}, request))
