from rest_framework.routers import DefaultRouter

from .views import ProfessionalViewSet, SpecialtyViewSet

router = DefaultRouter(trailing_slash=False)
router.register("professionals", ProfessionalViewSet, basename="professional")
router.register("specialties", SpecialtyViewSet, basename="specialty")

urlpatterns = router.urls
