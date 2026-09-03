from rest_framework import status, viewsets
from rest_framework.response import Response

from .responses import envelope


class EnvelopeRetrieveMixin:
    """`retrieve` no envelope padrao {data, meta}. `list` fica por conta da
    paginacao (ja gera {data, pagination})."""

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(envelope(serializer.data, request))


class EnvelopeModelViewSet(EnvelopeRetrieveMixin, viewsets.ModelViewSet):
    """ModelViewSet que responde no envelope padrao {data, meta} da API.

    `destroy` continua 204 sem corpo — so retrieve/create/update precisam
    do envelope.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            envelope(serializer.data, request), status=status.HTTP_201_CREATED, headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(envelope(serializer.data, request))
