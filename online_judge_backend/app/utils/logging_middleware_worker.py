import logging
from prometheus_client import Counter, Histogram, start_http_server

from .logging_utils import configure_logging


# Configure logger to output JSON
configure_logging()
logger = logging.getLogger("worker")

# Prometheus metrics
JOB_COUNT = Counter(
    "worker_jobs_total",
    "Total jobs processed",
    ["result"],
)
JOB_DURATION = Histogram(
    "worker_job_duration_seconds",
    "Job processing time in seconds",
)

def start_metrics_server(port: int = 8001) -> None:
    """Expose Prometheus metrics on the given port."""
    start_http_server(port)
