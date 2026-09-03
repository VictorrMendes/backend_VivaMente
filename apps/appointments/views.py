from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.audit.services import log_action
from apps.professionals.models import Professional
from config.mixins import ProfessionalScopedQuerysetMixin
from config.responses import envelope
from config.viewsets import EnvelopeModelViewSet

from . import services
from .models import Appointment, AvailabilitySlot
from .serializers import (
    AppointmentSelfWriteSerializer,
    AppointmentSerializer,
    AppointmentWriteSerializer,
    AvailabilitySlotSelfWriteSerializer,
    AvailabilitySlotSerializer,
    AvailabilitySlotWriteSerializer,
)


class AvailabilitySlotViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    queryset = AvailabilitySlot.objects.select_related("professional")
    filterset_fields = ["professional", "is_blocked"]
    ordering_fields = ["starts_at"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AvailabilitySlotSerializer
        if self.request.user.role != User.ADMIN:
            return AvailabilitySlotSelfWriteSerializer
        return AvailabilitySlotWriteSerializer

    def perform_create(self, serializer):
        services.create_availability_slot(self.request.user, serializer)
        log_action(self.request.user, "create", "availability_slot", serializer.instance.id)

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", "availability_slot", instance.id)
        instance.delete()


class AppointmentViewSet(ProfessionalScopedQuerysetMixin, EnvelopeModelViewSet):
    queryset = Appointment.objects.select_related("professional", "client", "service")
    filterset_fields = ["status", "professional", "client"]
    ordering_fields = ["starts_at", "status"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AppointmentSerializer
        if self.request.user.role != User.ADMIN:
            return AppointmentSelfWriteSerializer
        return AppointmentWriteSerializer

    def perform_create(self, serializer):
        services.create_appointment(self.request.user, serializer)
        log_action(self.request.user, "create", "appointment", serializer.instance.id)

    def perform_update(self, serializer):
        services.update_appointment(serializer)

    @action(detail=True, methods=["patch"])
    def confirm(self, request, pk=None):
        return self._transition(request, Appointment.CONFIRMED)

    @action(detail=True, methods=["patch"])
    def cancel(self, request, pk=None):
        return self._transition(request, Appointment.CANCELLED)

    @action(detail=True, methods=["patch"])
    def complete(self, request, pk=None):
        return self._transition(request, Appointment.COMPLETED)

    def _transition(self, request, new_status):
        appointment = self.get_object()
        services.transition_status(appointment, new_status)
        log_action(request.user, new_status.lower(), "appointment", appointment.id)
        return Response(envelope(AppointmentSerializer(appointment).data, request))


class PublicAvailableSlotsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public-available-slots"

    def get(self, request, slug):
        professional = get_object_or_404(Professional, slug=slug, is_public=True)
        slots = services.list_free_slots(professional)
        return Response(envelope(AvailabilitySlotSerializer(slots, many=True).data, request))
