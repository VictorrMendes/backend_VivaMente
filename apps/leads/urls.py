from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LeadViewSet, PublicAppointmentRequestView

router = DefaultRouter(trailing_slash=False)
router.register("leads", LeadViewSet, basename="lead")

urlpatterns = router.urls + [
    path("public/appointment-requests", PublicAppointmentRequestView.as_view()),
]
