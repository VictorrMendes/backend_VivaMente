from rest_framework.routers import DefaultRouter

from .views import ClinicalRecordViewSet

router = DefaultRouter(trailing_slash=False)
router.register("clinical-records", ClinicalRecordViewSet, basename="clinical-record")

urlpatterns = router.urls
