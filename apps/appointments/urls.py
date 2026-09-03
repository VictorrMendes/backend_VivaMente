from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AppointmentViewSet, AvailabilitySlotViewSet, PublicAvailableSlotsView

router = DefaultRouter(trailing_slash=False)
router.register("availability", AvailabilitySlotViewSet, basename="availability")
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls + [
    path("public/professionals/<slug:slug>/available-slots", PublicAvailableSlotsView.as_view()),
]
