import logging
from time import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app

from .logging_utils import configure_logging

# Basic logger setup with JSON output
configure_logging()
logger = logging.getLogger("online_judge")

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    ["method", "endpoint"],
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time()
        response = await call_next(request)
        process_time = time() - start_time
        method = request.method
        path = request.url.path
        status = response.status_code

        REQUEST_COUNT.labels(method, path, str(status)).inc()
        REQUEST_LATENCY.labels(method, path).observe(process_time)
        logger.info(
            "%s %s %s %.3fs", method, path, status, process_time
        )
        return response

# ASGI app exposing Prometheus metrics
metrics_app = make_asgi_app()
