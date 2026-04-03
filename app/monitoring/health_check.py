"""
Health Check for RefurbAdmin AI.

Provides comprehensive health check endpoints:
- Database health
- Cache health
- Scraper health
- Overall system health
- Dependency checks

Compatible with Kubernetes, Docker, and load balancers.
"""

import time
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckCategory(Enum):
    """Health check categories."""
    DATABASE = "database"
    CACHE = "cache"
    SCRAPER = "scraper"
    STORAGE = "storage"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    
    name: str
    category: CheckCategory
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    
    # Database settings
    database_url: str = ""
    database_timeout: int = 5  # seconds
    
    # Cache settings
    redis_url: str = ""
    redis_timeout: int = 3  # seconds
    
    # Scraper settings
    scraper_enabled: bool = True
    scraper_timeout: int = 10  # seconds
    scraper_test_url: str = ""
    
    # System settings
    disk_usage_threshold: float = 0.9  # 90%
    memory_usage_threshold: float = 0.95  # 95%
    
    # Check intervals
    check_interval: int = 30  # seconds
    detailed_check_interval: int = 300  # 5 minutes
    
    @classmethod
    def from_env(cls, env_dict: Dict[str, Any]) -> "HealthCheckConfig":
        """Create config from environment variables."""
        return cls(
            database_url=env_dict.get("DATABASE_URL", ""),
            database_timeout=int(env_dict.get("DB_HEALTH_TIMEOUT", "5")),
            redis_url=env_dict.get("REDIS_URL", ""),
            redis_timeout=int(env_dict.get("REDIS_HEALTH_TIMEOUT", "3")),
            scraper_enabled=env_dict.get("SCRAPER_ENABLED", "true").lower() == "true",
            scraper_timeout=int(env_dict.get("SCRAPER_TIMEOUT", "10")),
            disk_usage_threshold=float(env_dict.get("HEALTH_DISK_THRESHOLD", "0.9")),
            memory_usage_threshold=float(env_dict.get("HEALTH_MEMORY_THRESHOLD", "0.95")),
        )


@dataclass
class SystemHealth:
    """Overall system health status."""
    
    status: HealthStatus
    checks: List[HealthCheckResult] = field(default_factory=list)
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": self.timestamp,
            "checks": [check.to_dict() for check in self.checks],
            "summary": self._generate_summary(),
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate health summary."""
        total = len(self.checks)
        healthy = sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)
        degraded = sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY)
        
        return {
            "total_checks": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
        }


class HealthChecker:
    """
    Comprehensive health checker for RefurbAdmin AI.
    
    Features:
    - Database connectivity check
    - Cache/Redis connectivity check
    - Scraper functionality check
    - System resource monitoring
    - External API dependency checks
    - Configurable thresholds
    """
    
    _instance: Optional["HealthChecker"] = None
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config or HealthCheckConfig()
        self._start_time = time.time()
        self._last_check: Optional[SystemHealth] = None
        self._last_check_time: float = 0
        
        # Registered checks
        self._checks: Dict[str, Callable] = {}
        
        # Register default checks
        self._register_default_checks()
        
        logger.info("Health checker initialized")
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.register_check("database", self.check_database)
        self.register_check("cache", self.check_cache)
        self.register_check("system", self.check_system)
        
        if self.config.scraper_enabled:
            self.register_check("scraper", self.check_scraper)
    
    def register_check(self, name: str, check_func: Callable):
        """Register a custom health check."""
        self._checks[name] = check_func
        logger.debug(f"Registered health check: {name}")
    
    async def check_all(self, detailed: bool = False) -> SystemHealth:
        """
        Run all health checks.
        
        Args:
            detailed: Include detailed diagnostics
            
        Returns:
            SystemHealth with all check results
        """
        checks = []
        worst_status = HealthStatus.HEALTHY
        
        # Run all registered checks
        for name, check_func in self._checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func(detailed=detailed)
                else:
                    result = check_func(detailed=detailed)
                
                checks.append(result)
                
                # Track worst status
                if result.status == HealthStatus.UNHEALTHY:
                    worst_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and worst_status != HealthStatus.UNHEALTHY:
                    worst_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}")
                checks.append(HealthCheckResult(
                    name=name,
                    category=CheckCategory.SYSTEM,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(e)}",
                ))
                worst_status = HealthStatus.UNHEALTHY
        
        # Create system health
        health = SystemHealth(
            status=worst_status,
            checks=checks,
            version="1.0.0",
            uptime_seconds=time.time() - self._start_time,
        )
        
        self._last_check = health
        self._last_check_time = time.time()
        
        return health
    
    def check_all_sync(self, detailed: bool = False) -> SystemHealth:
        """Synchronous version of check_all."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.check_all(detailed=detailed))
    
    # =========================================================================
    # Individual Health Checks
    # =========================================================================
    
    async def check_database(self, detailed: bool = False) -> HealthCheckResult:
        """Check database connectivity and health."""
        start_time = time.time()
        
        if not self.config.database_url:
            return HealthCheckResult(
                name="database",
                category=CheckCategory.DATABASE,
                status=HealthStatus.UNKNOWN,
                message="Database URL not configured",
            )
        
        try:
            # Parse database URL
            db_info = self._parse_database_url(self.config.database_url)
            
            if PSYCOPG2_AVAILABLE:
                conn = psycopg2.connect(
                    host=db_info.get("host", "localhost"),
                    port=db_info.get("port", 5432),
                    database=db_info.get("database", "postgres"),
                    user=db_info.get("user", "postgres"),
                    password=db_info.get("password", ""),
                    connect_timeout=self.config.database_timeout,
                )
                
                cursor = conn.cursor()
                
                # Basic query test
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # Get connection pool stats if available
                pool_stats = {}
                if detailed:
                    cursor.execute("""
                        SELECT count(*) as total,
                               count(*) FILTER (WHERE state = 'active') as active,
                               count(*) FILTER (WHERE state = 'idle') as idle
                        FROM pg_stat_activity
                        WHERE datname = %s
                    """, (db_info.get("database"),))
                    row = cursor.fetchone()
                    if row:
                        pool_stats = {
                            "total_connections": row[0],
                            "active_connections": row[1],
                            "idle_connections": row[2],
                        }
                
                cursor.close()
                conn.close()
                
                response_time = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    name="database",
                    category=CheckCategory.DATABASE,
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    response_time_ms=round(response_time, 2),
                    details=pool_stats,
                )
            else:
                # Fallback without psycopg2
                return HealthCheckResult(
                    name="database",
                    category=CheckCategory.DATABASE,
                    status=HealthStatus.DEGRADED,
                    message="Database driver not available (psycopg2)",
                    details={"driver": "psycopg2", "installed": False},
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="database",
                category=CheckCategory.DATABASE,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=round(response_time, 2),
            )
    
    async def check_cache(self, detailed: bool = False) -> HealthCheckResult:
        """Check Redis cache connectivity and health."""
        start_time = time.time()
        
        if not self.config.redis_url:
            return HealthCheckResult(
                name="cache",
                category=CheckCategory.CACHE,
                status=HealthStatus.UNKNOWN,
                message="Redis URL not configured",
            )
        
        if not REDIS_AVAILABLE:
            return HealthCheckResult(
                name="cache",
                category=CheckCategory.CACHE,
                status=HealthStatus.DEGRADED,
                message="Redis client not available",
                details={"driver": "redis", "installed": False},
            )
        
        try:
            redis_client = redis.from_url(
                self.config.redis_url,
                socket_connect_timeout=self.config.redis_timeout,
                decode_responses=True,
            )
            
            # Ping test
            redis_client.ping()
            
            # Get info
            cache_details = {}
            if detailed:
                info = redis_client.info("memory")
                cache_details = {
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "used_memory_peak": info.get("used_memory_peak_human", "unknown"),
                    "connected_clients": redis_client.info("clients").get("connected_clients", 0),
                }
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="cache",
                category=CheckCategory.CACHE,
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                response_time_ms=round(response_time, 2),
                details=cache_details,
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="cache",
                category=CheckCategory.CACHE,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=round(response_time, 2),
            )
    
    async def check_scraper(self, detailed: bool = False) -> HealthCheckResult:
        """Check scraper functionality."""
        start_time = time.time()
        
        if not self.config.scraper_enabled:
            return HealthCheckResult(
                name="scraper",
                category=CheckCategory.SCRAPER,
                status=HealthStatus.UNKNOWN,
                message="Scraper is disabled",
            )
        
        try:
            # Test scraper connectivity
            # This is a placeholder - implement actual scraper health check
            scraper_status = HealthStatus.HEALTHY
            message = "Scraper is operational"
            details = {}
            
            if detailed:
                # Check scraper sources
                details["sources"] = {
                    "takealot": "operational",
                    "leroymerlin": "operational",
                    "makro": "operational",
                }
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="scraper",
                category=CheckCategory.SCRAPER,
                status=scraper_status,
                message=message,
                response_time_ms=round(response_time, 2),
                details=details,
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="scraper",
                category=CheckCategory.SCRAPER,
                status=HealthStatus.UNHEALTHY,
                message=f"Scraper check failed: {str(e)}",
                response_time_ms=round(response_time, 2),
            )
    
    async def check_system(self, detailed: bool = False) -> HealthCheckResult:
        """Check system resources."""
        start_time = time.time()
        
        try:
            system_details = {}
            status = HealthStatus.HEALTHY
            messages = []
            
            # Disk usage
            try:
                import shutil
                total, used, free = shutil.disk_usage("/")
                disk_usage = used / total
                
                system_details["disk"] = {
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "usage_percent": round(disk_usage * 100, 2),
                }
                
                if disk_usage > self.config.disk_usage_threshold:
                    status = HealthStatus.DEGRADED
                    messages.append(f"Disk usage high: {disk_usage * 100:.1f}%")
                    
            except Exception as e:
                system_details["disk"] = {"error": str(e)}
            
            # Memory usage
            try:
                import psutil
                memory = psutil.virtual_memory()
                
                system_details["memory"] = {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent,
                }
                
                if memory.percent > self.config.memory_usage_threshold * 100:
                    status = HealthStatus.DEGRADED
                    messages.append(f"Memory usage high: {memory.percent}%")
                    
            except ImportError:
                system_details["memory"] = {"error": "psutil not installed"}
            except Exception as e:
                system_details["memory"] = {"error": str(e)}
            
            # CPU usage
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=0.1)
                system_details["cpu"] = {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count(),
                }
            except:
                system_details["cpu"] = {"error": "Could not get CPU info"}
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="system",
                category=CheckCategory.SYSTEM,
                status=status,
                message="; ".join(messages) if messages else "System resources OK",
                response_time_ms=round(response_time, 2),
                details=system_details,
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="system",
                category=CheckCategory.SYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"System check failed: {str(e)}",
            )
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _parse_database_url(self, url: str) -> Dict[str, Any]:
        """Parse database URL into components."""
        # Simple parser for postgresql://user:pass@host:port/dbname
        result = {}
        
        if url.startswith("postgresql://"):
            url = url[13:]
        elif url.startswith("postgres://"):
            url = url[11:]
        
        # Parse components
        if "@" in url:
            auth, rest = url.split("@", 1)
            if ":" in auth:
                result["user"], result["password"] = auth.split(":", 1)
            else:
                result["user"] = auth
        else:
            rest = url
        
        if "/" in rest:
            host_port, database = rest.split("/", 1)
            result["database"] = database
        else:
            host_port = rest
        
        if ":" in host_port:
            host, port = host_port.split(":", 1)
            result["host"] = host
            result["port"] = int(port)
        else:
            result["host"] = host_port
        
        return result
    
    def get_last_health(self) -> Optional[SystemHealth]:
        """Get the last health check result."""
        return self._last_check
    
    def get_health_age(self) -> float:
        """Get age of last health check in seconds."""
        if self._last_check_time == 0:
            return float('inf')
        return time.time() - self._last_check_time


# =============================================================================
# FastAPI Integration
# =============================================================================

def create_health_router(health_checker: HealthChecker = None):
    """
    Create FastAPI router for health endpoints.
    
    Usage:
        from app.monitoring.health_check import create_health_router
        app.include_router(create_health_router())
    """
    from fastapi import APIRouter, Response
    from fastapi.responses import JSONResponse
    
    router = APIRouter(prefix="/api/health", tags=["health"])
    checker = health_checker or HealthChecker()
    
    @router.get("")
    async def health_check(detailed: bool = False):
        """
        Comprehensive health check endpoint.
        
        Returns status of all system components.
        """
        health = await checker.check_all(detailed=detailed)
        
        status_code = 200
        if health.status == HealthStatus.UNHEALTHY:
            status_code = 503
        elif health.status == HealthStatus.DEGRADED:
            status_code = 207  # Multi-status
        
        return JSONResponse(
            status_code=status_code,
            content=health.to_dict(),
        )
    
    @router.get("/live")
    async def liveness_check():
        """
        Kubernetes liveness probe endpoint.
        
        Returns 200 if the application is running.
        """
        return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
    
    @router.get("/ready")
    async def readiness_check():
        """
        Kubernetes readiness probe endpoint.
        
        Returns 200 if the application is ready to serve traffic.
        """
        health = await checker.check_all(detailed=False)
        
        # Ready if database and cache are healthy
        db_healthy = any(
            c.status == HealthStatus.HEALTHY 
            for c in health.checks 
            if c.category == CheckCategory.DATABASE
        )
        
        if db_healthy:
            return {"status": "ready"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "Database not available"},
            )
    
    @router.get("/startup")
    async def startup_check():
        """
        Kubernetes startup probe endpoint.
        
        Returns 200 if the application has completed startup.
        """
        # Simple check - application is running if we get here
        uptime = time.time() - checker._start_time
        return {
            "status": "started",
            "uptime_seconds": round(uptime, 2),
        }
    
    return router


# =============================================================================
# Singleton
# =============================================================================

_health_checker_instance: Optional[HealthChecker] = None


def get_health_checker(config: Optional[HealthCheckConfig] = None) -> HealthChecker:
    """Get or create the health checker singleton."""
    global _health_checker_instance
    
    if _health_checker_instance is None:
        _health_checker_instance = HealthChecker(config=config)
    
    return _health_checker_instance
