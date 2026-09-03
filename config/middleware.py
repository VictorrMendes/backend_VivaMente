import logging
import time
import uuid

from .logging import request_id_var

access_logger = logging.getLogger("api.access")


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = f"req_{uuid.uuid4().hex[:12]}"
        token = request_id_var.set(request.request_id)
        start = time.monotonic()
        try:
            response = self.get_response(request)
            duration_ms = (time.monotonic() - start) * 1000
            access_logger.info(
                "%s %s -> %s (%.1fms)",
                request.method,
                request.get_full_path(),
                response.status_code,
                duration_ms,
            )
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = request.request_id
        return response
