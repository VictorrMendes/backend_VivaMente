from django.utils import timezone


def envelope(data, request=None):
    return {
        "data": data,
        "meta": {
            "request_id": getattr(request, "request_id", None),
            "timestamp": timezone.now().isoformat(),
        },
    }
