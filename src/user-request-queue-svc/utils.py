"""
Utility functions for user-request-queue-svc
"""
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any
import time

# Prometheus metrics
BATCHES_PROCESSED_TOTAL = Counter(
    'batches_processed_total',
    'Total number of batches processed',
    ['status']
)

TRANSACTIONS_PROCESSED_TOTAL = Counter(
    'transactions_processed_total',
    'Total number of transactions processed',
    ['status']
)

BATCH_PROCESSING_DURATION = Histogram(
    'batch_processing_duration_seconds',
    'Time spent processing batches',
    ['status']
)

QUEUE_SIZE = Gauge(
    'queue_size',
    'Current number of pending requests in queue'
)

EXTERNAL_SERVICE_RESPONSE_TIME = Histogram(
    'external_service_response_time_seconds',
    'Time spent waiting for external service responses',
    ['service', 'status']
)

FAILED_BATCHES_TOTAL = Counter(
    'failed_batches_total',
    'Total number of failed batches',
    ['error_type']
)

logger = structlog.get_logger(__name__)


def setup_logging(log_level: str = "INFO"):
    """Setup structured logging"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_metrics() -> str:
    """Get Prometheus metrics in text format"""
    return generate_latest()


def record_batch_processed(status: str, count: int = 1):
    """Record batch processing metrics"""
    BATCHES_PROCESSED_TOTAL.labels(status=status).inc(count)


def record_transactions_processed(status: str, count: int):
    """Record transaction processing metrics"""
    TRANSACTIONS_PROCESSED_TOTAL.labels(status=status).inc(count)


def record_batch_processing_time(status: str, duration: float):
    """Record batch processing duration"""
    BATCH_PROCESSING_DURATION.labels(status=status).observe(duration)


def record_queue_size(size: int):
    """Record current queue size"""
    QUEUE_SIZE.set(size)


def record_external_service_time(service: str, status: str, duration: float):
    """Record external service response time"""
    EXTERNAL_SERVICE_RESPONSE_TIME.labels(service=service, status=status).observe(duration)


def record_failed_batch(error_type: str, count: int = 1):
    """Record failed batch metrics"""
    FAILED_BATCHES_TOTAL.labels(error_type=error_type).inc(count)


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, metric_func, *args, **kwargs):
        self.metric_func = metric_func
        self.args = args
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.metric_func(*self.args, **self.kwargs, duration=duration)


def create_error_response(error: str, detail: str = None) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": error,
        "detail": detail,
        "timestamp": time.time()
    }


def validate_tier_amounts(tier1: float, tier2: float, tier3: float) -> bool:
    """Validate that tier amounts are non-negative"""
    return tier1 >= 0 and tier2 >= 0 and tier3 >= 0


def format_decimal(value) -> str:
    """Format decimal value for logging"""
    if hasattr(value, 'quantize'):
        return f"{value:.8f}"
    return str(value)
