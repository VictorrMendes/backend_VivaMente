from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.professionals.models import Professional
from config.responses import envelope

from .serializers import PublicProfessionalSerializer, PublicProfileUpdateSerializer


class PublicProfessionalProfileView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public-professional-profile"

    def get(self, request, slug):
        professional = get_object_or_404(Professional, slug=slug, is_public=True)
        return Response(envelope(PublicProfessionalSerializer(professional).data, request))


class PublicProfileUpdateView(APIView):
    def patch(self, request, pk):
        professional = get_object_or_404(Professional, pk=pk)
        user = request.user
        if user.role != User.ADMIN and professional.user_id != user.id:
            raise PermissionDenied("Você só pode editar o próprio perfil público.")

        serializer = PublicProfileUpdateSerializer(professional, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(envelope(PublicProfessionalSerializer(professional).data, request))
