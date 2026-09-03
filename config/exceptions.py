import logging
import uuid

from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("api.errors")

PROBLEM_TYPE_BASE = "https://api.vivamenteterapias.com.br/errors/"

_TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
}

_SLUGS = {
    400: "validation-error",
    401: "unauthorized",
    403: "forbidden",
    404: "not-found",
    405: "method-not-allowed",
    409: "conflict",
    422: "unprocessable-entity",
    429: "rate-limited",
    500: "internal-error",
}


def _detail_from(data):
    if isinstance(data, dict):
        for key in ("detail", "message"):
            if key in data:
                return str(data[key])
        return "; ".join(f"{k}: {v}" for k, v in data.items())
    if isinstance(data, list):
        return "; ".join(str(item) for item in data)
    return str(data)


def rfc9457_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None) or str(uuid.uuid4())

    if response is None:
        # Excecao nao mapeada pelo DRF (bug real, nao um erro de cliente).
        # Nunca deixa o Django devolver a pagina de debug em HTML pra um
        # cliente de API - loga o stack trace pro request_id e responde
        # RFC 9457 generico, sem detalhe interno.
        logger.exception("Erro interno nao tratado", extra={"request_id": request_id})
        return Response(
            {
                "type": PROBLEM_TYPE_BASE + "internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Ocorreu um erro inesperado.",
                "request_id": request_id,
            },
            status=500,
        )

    status = response.status_code

    response.data = {
        "type": PROBLEM_TYPE_BASE + _SLUGS.get(status, "error"),
        "title": _TITLES.get(status, "Error"),
        "status": status,
        "detail": _detail_from(response.data),
        "request_id": request_id,
    }
    return response
