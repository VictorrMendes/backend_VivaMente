import contextvars
import json
import logging

request_id_var = contextvars.ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Log estruturado em JSON (1 linha por evento), com o request_id da
    requisicao atual (via contextvar, setado por config.middleware.RequestIDMiddleware)
    anexado automaticamente - permite correlacionar logs com o X-Request-ID
    devolvido ao cliente e com o campo request_id do envelope de erro."""

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
