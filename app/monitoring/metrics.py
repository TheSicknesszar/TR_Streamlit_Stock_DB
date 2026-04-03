"""
Prometheus Metrics for RefurbAdmin AI.

Provides comprehensive metrics collection:
- Request count and response time histogram
- Database connection pool metrics
- Cache hit rate
- Business metrics (inventory, sales)
- System health metrics

Compatible with Prometheus and Grafana.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from collections import defaultdict
import json

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Summary,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
        start_http_server,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Prometheus Metrics Definitions
# =============================================================================

# Request metrics
REQUEST_COUNT = Counter(
    'refurbadmin_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status', 'handler']
) if PROMETHEUS_AVAILABLE else None

REQUEST_DURATION = Histogram(
    'refurbadmin_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint', 'handler'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
) if PROMETHEUS_AVAILABLE else None

REQUEST_IN_PROGRESS = Gauge(
    'refurbadmin_requests_in_progress',
    'Number of requests currently in progress',
    ['method', 'endpoint']
) if PROMETHEUS_AVAILABLE else None

# Database metrics
DB_CONNECTION_POOL_SIZE = Gauge(
    'refurbadmin_db_pool_size',
    'Database connection pool size'
) if PROMETHEUS_AVAILABLE else None

DB_CONNECTION_POOL_USED = Gauge(
    'refurbadmin_db_pool_used',
    'Number of database connections currently in use'
) if PROMETHEUS_AVAILABLE else None

DB_QUERY_DURATION = Histogram(
    'refurbadmin_db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
) if PROMETHEUS_AVAILABLE else None

DB_CONNECTION_ERRORS = Counter(
    'refurbadmin_db_connection_errors_total',
    'Total number of database connection errors'
) if PROMETHEUS_AVAILABLE else None

# Cache metrics
CACHE_REQUESTS = Counter(
    'refurbadmin_cache_requests_total',
    'Total number of cache requests',
    ['cache_type', 'operation']
) if PROMETHEUS_AVAILABLE else None

CACHE_HITS = Counter(
    'refurbadmin_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
) if PROMETHEUS_AVAILABLE else None

CACHE_MISSES = Counter(
    'refurbadmin_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
) if PROMETHEUS_AVAILABLE else None

CACHE_SIZE = Gauge(
    'refurbadmin_cache_size',
    'Current cache size',
    ['cache_type']
) if PROMETHEUS_AVAILABLE else None

# Business metrics
INVENTORY_COUNT = Gauge(
    'refurbadmin_inventory_items_total',
    'Total number of inventory items',
    ['category', 'status']
) if PROMETHEUS_AVAILABLE else None

INVENTORY_VALUE = Gauge(
    'refurbadmin_inventory_value_zar',
    'Total inventory value in ZAR (South African Rand)',
    ['category']
) if PROMETHEUS_AVAILABLE else None

SALES_COUNT = Counter(
    'refurbadmin_sales_total',
    'Total number of sales',
    ['payment_method']
) if PROMETHEUS_AVAILABLE else None

SALES_REVENUE = Counter(
    'refurbadmin_sales_revenue_zar',
    'Total sales revenue in ZAR',
    ['payment_method']
) if PROMETHEUS_AVAILABLE else None

QUOTES_CREATED = Counter(
    'refurbadmin_quotes_created_total',
    'Total number of quotes created'
) if PROMETHEUS_AVAILABLE else None

QUOTES_CONVERTED = Counter(
    'refurbadmin_quotes_converted_total',
    'Total number of quotes converted to sales'
) if PROMETHEUS_AVAILABLE else None

# Security metrics
AUTH_ATTEMPTS = Counter(
    'refurbadmin_auth_attempts_total',
    'Total authentication attempts',
    ['method', 'success']
) if PROMETHEUS_AVAILABLE else None

RATE_LIMIT_HITS = Counter(
    'refurbadmin_rate_limit_hits_total',
    'Total number of rate limit hits',
    ['endpoint', 'tier']
) if PROMETHEUS_AVAILABLE else None

SECURITY_EVENTS = Counter(
    'refurbadmin_security_events_total',
    'Total security events',
    ['event_type', 'severity']
) if PROMETHEUS_AVAILABLE else None

# System metrics
PROCESS_MEMORY = Gauge(
    'refurbadmin_process_memory_bytes',
    'Process memory usage in bytes',
    ['type']
) if PROMETHEUS_AVAILABLE else None

PROCESS_CPU = Gauge(
    'refurbadmin_process_cpu_percent',
    'Process CPU usage percentage'
) if PROMETHEUS_AVAILABLE else None

UPTIME = Gauge(
    'refurbadmin_uptime_seconds',
    'Application uptime in seconds'
) if PROMETHEUS_AVAILABLE else None


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    
    enabled: bool = True
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    prefix: str = "refurbadmin"
    
    # Collection intervals
    system_metrics_interval: int = 60  # seconds
    
    # Retention
    max_history_points: int = 1000
    
    @classmethod
    def from_env(cls, env_dict: Dict[str, Any]) -> "MetricsConfig":
        """Create config from environment variables."""
        return cls(
            enabled=env_dict.get("METRICS_ENABLED", "true").lower() == "true",
            prometheus_enabled=env_dict.get("PROMETHEUS_ENABLED", "true").lower() == "true",
            prometheus_port=int(env_dict.get("PROMETHEUS_PORT", "9090")),
            prefix=env_dict.get("METRICS_PREFIX", "refurbadmin"),
        )


class MetricsCollector:
    """
    Central metrics collector for RefurbAdmin AI.
    
    Features:
    - Prometheus metrics export
    - In-memory metrics storage
    - Business metrics tracking
    - Performance monitoring
    """
    
    _instance: Optional["MetricsCollector"] = None
    _lock = Lock()
    
    def __new__(cls, config: Optional[MetricsConfig] = None) -> "MetricsCollector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, config: Optional[MetricsConfig] = None):
        if self._initialized:
            return
        
        self.config = config or MetricsConfig()
        self._start_time = time.time()
        
        # In-memory metrics storage
        self._custom_metrics: Dict[str, Any] = defaultdict(list)
        self._gauges: Dict[str, float] = {}
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Cache hit rate tracking
        self._cache_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"hits": 0, "misses": 0}
        )
        
        # Database pool tracking
        self._db_pool_stats = {"size": 0, "used": 0}
        
        if self.config.enabled and self.config.prometheus_enabled and PROMETHEUS_AVAILABLE:
            self._start_prometheus_server()
            logger.info("Prometheus metrics server started")
        elif not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, using in-memory metrics only")
        
        self._initialized = True
        logger.info("Metrics collector initialized")
    
    def _start_prometheus_server(self):
        """Start Prometheus metrics HTTP server."""
        try:
            start_http_server(self.config.prometheus_port)
            logger.info(f"Prometheus metrics available at http://localhost:{self.config.prometheus_port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")
    
    # =========================================================================
    # Request Metrics
    # =========================================================================
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        handler: str = "unknown"
    ):
        """Record an API request."""
        if not self.config.enabled:
            return
        
        status_str = str(status)
        status_category = f"{status // 100}xx"
        
        if PROMETHEUS_AVAILABLE and REQUEST_COUNT:
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status_category,
                handler=handler
            ).inc()
        
        if PROMETHEUS_AVAILABLE and REQUEST_DURATION:
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
                handler=handler
            ).observe(duration)
        
        # Store in-memory for fallback
        self._counters[f"requests:{method}:{endpoint}:{status_category}"] += 1
    
    @contextmanager
    def request_timer(self, method: str, endpoint: str, handler: str = "unknown"):
        """Context manager for timing requests."""
        start_time = time.time()
        
        if PROMETHEUS_AVAILABLE and REQUEST_IN_PROGRESS:
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            
            if PROMETHEUS_AVAILABLE and REQUEST_IN_PROGRESS:
                REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
    
    # =========================================================================
    # Database Metrics
    # =========================================================================
    
    def record_db_query(self, query_type: str, table: str, duration: float):
        """Record a database query."""
        if not self.config.enabled:
            return
        
        if PROMETHEUS_AVAILABLE and DB_QUERY_DURATION:
            DB_QUERY_DURATION.labels(
                query_type=query_type,
                table=table
            ).observe(duration)
    
    def update_db_pool_stats(self, size: int, used: int):
        """Update database pool statistics."""
        self._db_pool_stats = {"size": size, "used": used}
        
        if PROMETHEUS_AVAILABLE:
            if DB_CONNECTION_POOL_SIZE:
                DB_CONNECTION_POOL_SIZE.set(size)
            if DB_CONNECTION_POOL_USED:
                DB_CONNECTION_POOL_USED.set(used)
    
    def record_db_connection_error(self):
        """Record a database connection error."""
        if PROMETHEUS_AVAILABLE and DB_CONNECTION_ERRORS:
            DB_CONNECTION_ERRORS.inc()
    
    # =========================================================================
    # Cache Metrics
    # =========================================================================
    
    def record_cache_hit(self, cache_type: str = "default"):
        """Record a cache hit."""
        self._cache_stats[cache_type]["hits"] += 1
        
        if PROMETHEUS_AVAILABLE and CACHE_HITS:
            CACHE_HITS.labels(cache_type=cache_type).inc()
        
        if PROMETHEUS_AVAILABLE and CACHE_REQUESTS:
            CACHE_REQUESTS.labels(cache_type=cache_type, operation="get").inc()
    
    def record_cache_miss(self, cache_type: str = "default"):
        """Record a cache miss."""
        self._cache_stats[cache_type]["misses"] += 1
        
        if PROMETHEUS_AVAILABLE and CACHE_MISSES:
            CACHE_MISSES.labels(cache_type=cache_type).inc()
        
        if PROMETHEUS_AVAILABLE and CACHE_REQUESTS:
            CACHE_REQUESTS.labels(cache_type=cache_type, operation="get").inc()
    
    def record_cache_operation(
        self,
        operation: str,
        cache_type: str = "default"
    ):
        """Record a cache operation (set, delete, etc.)."""
        if PROMETHEUS_AVAILABLE and CACHE_REQUESTS:
            CACHE_REQUESTS.labels(cache_type=cache_type, operation=operation).inc()
    
    def update_cache_size(self, size: int, cache_type: str = "default"):
        """Update cache size."""
        if PROMETHEUS_AVAILABLE and CACHE_SIZE:
            CACHE_SIZE.labels(cache_type=cache_type).set(size)
    
    def get_cache_hit_rate(self, cache_type: str = "default") -> float:
        """Get cache hit rate for a cache type."""
        stats = self._cache_stats[cache_type]
        total = stats["hits"] + stats["misses"]
        
        if total == 0:
            return 0.0
        
        return stats["hits"] / total
    
    # =========================================================================
    # Business Metrics
    # =========================================================================
    
    def update_inventory_stats(
        self,
        total_items: int,
        total_value: float,
        by_category: Dict[str, Dict[str, Any]] = None
    ):
        """Update inventory metrics."""
        if PROMETHEUS_AVAILABLE:
            if INVENTORY_COUNT:
                INVENTORY_COUNT.set(total_items)
            if INVENTORY_VALUE:
                INVENTORY_VALUE.set(total_value)
    
    def record_sale(self, amount: float, payment_method: str = "unknown"):
        """Record a sale."""
        if PROMETHEUS_AVAILABLE:
            if SALES_COUNT:
                SALES_COUNT.labels(payment_method=payment_method).inc()
            if SALES_REVENUE:
                SALES_REVENUE.labels(payment_method=payment_method).inc(amount)
    
    def record_quote_created(self):
        """Record a quote creation."""
        if PROMETHEUS_AVAILABLE and QUOTES_CREATED:
            QUOTES_CREATED.inc()
    
    def record_quote_converted(self):
        """Record a quote conversion."""
        if PROMETHEUS_AVAILABLE and QUOTES_CONVERTED:
            QUOTES_CONVERTED.inc()
    
    # =========================================================================
    # Security Metrics
    # =========================================================================
    
    def record_auth_attempt(self, method: str, success: bool):
        """Record an authentication attempt."""
        if PROMETHEUS_AVAILABLE and AUTH_ATTEMPTS:
            AUTH_ATTEMPTS.labels(
                method=method,
                success="true" if success else "false"
            ).inc()
    
    def record_rate_limit_hit(self, endpoint: str, tier: str = "standard"):
        """Record a rate limit hit."""
        if PROMETHEUS_AVAILABLE and RATE_LIMIT_HITS:
            RATE_LIMIT_HITS.labels(
                endpoint=endpoint,
                tier=tier
            ).inc()
    
    def record_security_event(self, event_type: str, severity: str = "warning"):
        """Record a security event."""
        if PROMETHEUS_AVAILABLE and SECURITY_EVENTS:
            SECURITY_EVENTS.labels(
                event_type=event_type,
                severity=severity
            ).inc()
    
    # =========================================================================
    # System Metrics
    # =========================================================================
    
    def update_system_metrics(self):
        """Update system metrics (memory, CPU, uptime)."""
        if not self.config.enabled:
            return
        
        try:
            import psutil
            process = psutil.Process()
            
            # Memory
            mem_info = process.memory_info()
            if PROMETHEUS_AVAILABLE and PROCESS_MEMORY:
                PROCESS_MEMORY.labels(type="rss").set(mem_info.rss)
                PROCESS_MEMORY.labels(type="vms").set(mem_info.vms)
            
            # CPU
            cpu_percent = process.cpu_percent()
            if PROMETHEUS_AVAILABLE and PROCESS_CPU:
                PROCESS_CPU.set(cpu_percent)
            
        except ImportError:
            logger.debug("psutil not available, skipping system metrics")
        except Exception as e:
            logger.debug(f"Failed to collect system metrics: {e}")
        
        # Uptime
        uptime = time.time() - self._start_time
        if PROMETHEUS_AVAILABLE and UPTIME:
            UPTIME.set(uptime)
    
    # =========================================================================
    # Custom Metrics
    # =========================================================================
    
    def record_custom_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a custom metric."""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self._custom_metrics[key].append({
            "value": value,
            "timestamp": time.time(),
            "labels": labels or {}
        })
        
        # Trim old data
        if len(self._custom_metrics[key]) > self.config.max_history_points:
            self._custom_metrics[key] = self._custom_metrics[key][-self.config.max_history_points:]
    
    def get_custom_metric(self, name: str, labels: Dict[str, str] = None) -> list:
        """Get custom metric history."""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        return self._custom_metrics.get(key, [])
    
    # =========================================================================
    # Metrics Export
    # =========================================================================
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary."""
        metrics = {
            "uptime_seconds": time.time() - self._start_time,
            "cache": {},
            "database": self._db_pool_stats,
            "counters": dict(self._counters),
            "gauges": self._gauges,
            "custom": {},
        }
        
        # Cache hit rates
        for cache_type, stats in self._cache_stats.items():
            total = stats["hits"] + stats["misses"]
            metrics["cache"][cache_type] = {
                "hits": stats["hits"],
                "misses": stats["misses"],
                "hit_rate": stats["hits"] / total if total > 0 else 0.0,
            }
        
        # Custom metrics summaries
        for key, values in self._custom_metrics.items():
            if values:
                metrics["custom"][key] = {
                    "latest": values[-1]["value"],
                    "min": min(v["value"] for v in values),
                    "max": max(v["value"] for v in values),
                    "avg": sum(v["value"] for v in values) / len(values),
                    "count": len(values),
                }
        
        return metrics
    
    def generate_prometheus_metrics(self) -> str:
        """Generate Prometheus metrics output."""
        if PROMETHEUS_AVAILABLE:
            return generate_latest().decode('utf-8')
        return ""


# =============================================================================
# Decorators
# =============================================================================

def track_request(handler_name: str = None):
    """Decorator to track request metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            name = handler_name or func.__name__
            
            start_time = time.time()
            status = 200
            
            try:
                result = await func(*args, **kwargs)
                if hasattr(result, 'status_code'):
                    status = result.status_code
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time
                collector.record_request(
                    method="POST",  # Would need to be passed in
                    endpoint=name,
                    status=status,
                    duration=duration,
                    handler=name
                )
        
        return wrapper
    return decorator


# =============================================================================
# Singleton
# =============================================================================

_metrics_collector_instance: Optional[MetricsCollector] = None


def get_metrics_collector(config: Optional[MetricsConfig] = None) -> MetricsCollector:
    """Get or create the metrics collector singleton."""
    global _metrics_collector_instance
    
    if _metrics_collector_instance is None:
        _metrics_collector_instance = MetricsCollector(config=config)
    
    return _metrics_collector_instance


def init_metrics(config: Optional[MetricsConfig] = None) -> MetricsCollector:
    """Initialize metrics collector."""
    return get_metrics_collector(config)
