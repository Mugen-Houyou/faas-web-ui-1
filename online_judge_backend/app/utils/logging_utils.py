import json
import logging
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON log formatter for Filebeat/ELK."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        log_record = {
            "level": record.levelname,
            "time": datetime.utcfromtimestamp(record.created).isoformat(timespec="milliseconds") + "Z",
            "module": record.name,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger to output JSON formatted logs."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler])

