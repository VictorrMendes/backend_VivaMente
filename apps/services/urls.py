from rest_framework.routers import DefaultRouter

from .views import ServiceViewSet

router = DefaultRouter(trailing_slash=False)
router.register("services", ServiceViewSet, basename="service")

urlpatterns = router.urls
