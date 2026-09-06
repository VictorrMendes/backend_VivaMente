from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, viewsets
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
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @extend_schema(request=None, responses=NotificationSerializer)
    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        services.mark_read(notification)
        return Response(envelope(NotificationSerializer(notification).data, request))

    @extend_schema(request=None, responses=inline_serializer(
        "NotificationsReadResult", fields={"updated": serializers.IntegerField()},
    ))
    @action(detail=False, methods=["patch"], url_path="read-all")
    def mark_all_read(self, request):
        updated = services.mark_all_read(self.get_queryset())
        return Response(envelope({"updated": updated}, request))
