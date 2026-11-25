import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("service")
logger.setLevel(logging.INFO)
logger.addHandler(logging.FileHandler("events.log", encoding="utf-8"))

def log_event(trace_id, status, latency_us):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "latency_us": latency_us,
        "status": status,
    }
    logger.info(json.dumps(record))