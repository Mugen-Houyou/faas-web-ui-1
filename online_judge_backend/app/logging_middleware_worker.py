import logging
from prometheus_client import Counter, Histogram, start_http_server

# Basic logger setup for worker
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
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
