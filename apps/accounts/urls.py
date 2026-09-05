from django.urls import path

from .internal_views import IdentityUserSyncView
from .views import MeView

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path(
        "internal/identity/users/<str:firebase_uid>",
        IdentityUserSyncView.as_view(),
        name="internal-identity-user-sync",
    ),
]
