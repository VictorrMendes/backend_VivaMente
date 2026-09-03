from django.urls import path

from .views import PublicProfessionalProfileView, PublicProfileUpdateView

urlpatterns = [
    path("public/professionals/<slug:slug>", PublicProfessionalProfileView.as_view()),
    path("professionals/<int:pk>/public-profile", PublicProfileUpdateView.as_view()),
]
