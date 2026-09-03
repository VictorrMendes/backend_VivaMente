from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(request):
    return JsonResponse({"status": "ok"})


def health_database(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health", health),
    path("api/v1/health/database", health_database),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.professionals.urls")),
    path("api/v1/", include("apps.services.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema")),
]

if settings.DEBUG:
    from apps.accounts.views import FakeTokenView

    urlpatterns += [path("api/v1/dev/fake-token", FakeTokenView.as_view())]
