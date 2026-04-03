"""
Audit Logger for RefurbAdmin AI.

Provides comprehensive security audit logging for:
- All API requests
- Authentication events
- Data access and modifications
- POPIA compliance logging

Designed for South African POPIA (Protection of Personal Information Act) compliance.
"""

import json
import logging
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import threading
from collections import deque

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    
    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_PASSWORD_CHANGE = "auth.password.change"
    AUTH_PASSWORD_RESET = "auth.password.reset"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_MFA_ENABLED = "auth.mfa.enabled"
    AUTH_MFA_DISABLED = "auth.mfa.disabled"
    
    # API request events
    API_REQUEST = "api.request"
    API_RATE_LIMIT = "api.rate_limit"
    API_ERROR = "api.error"
    
    # Data access events
    DATA_READ = "data.read"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    
    # POPIA-specific events
    POPPIA_CONSENT_GRANTED = "popia.consent.granted"
    POPPIA_CONSENT_WITHDRAWN = "popia.consent.withdrawn"
    POPPIA_DATA_ACCESS_REQUEST = "popia.data.access_request"
    POPPIA_DATA_CORRECTION = "popia.data.correction"
    POPPIA_DATA_DELETION = "popia.data.deletion"
    POPPIA_DATA_BREACH = "popia.data.breach"
    
    # Admin events
    ADMIN_USER_CREATED = "admin.user.created"
    ADMIN_USER_UPDATED = "admin.user.updated"
    ADMIN_USER_DELETED = "admin.user.deleted"
    ADMIN_CONFIG_CHANGE = "admin.config.change"
    ADMIN_BACKUP = "admin.backup"
    ADMIN_RESTORE = "admin.restore"
    
    # Security events
    SECURITY_VIOLATION = "security.violation"
    SECURITY_SQL_INJECTION = "security.sql_injection"
    SECURITY_XSS_ATTEMPT = "security.xss_attempt"
    SECURITY_PATH_TRAVERSAL = "security.path_traversal"
    SECURITY_BRUTE_FORCE = "security.brute_force"


class EventSeverity(Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    Represents a single audit event.
    
    POPIA Compliance Fields:
    - purpose: Why the data was processed
    - data_subject: The person whose data is involved
    - consent: Whether consent was obtained
    """
    
    # Core fields
    event_id: str
    event_type: str
    timestamp: str
    severity: str
    
    # Actor information
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Request information
    endpoint: Optional[str] = None
    method: Optional[str] = None
    request_id: Optional[str] = None
    
    # Resource information
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    
    # Action details
    action: Optional[str] = None
    status: str = "success"
    status_code: Optional[int] = None
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # POPIA-specific fields
    popia_purpose: Optional[str] = None
    popia_data_subject: Optional[str] = None
    popia_consent_obtained: bool = False
    popia_retention_period: Optional[str] = None
    
    # Computed fields
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def get_hash(self) -> str:
        """Get hash of event for integrity verification."""
        event_str = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(event_str.encode()).hexdigest()


@dataclass
class AuditLogConfig:
    """Configuration for audit logging."""
    
    # Storage settings
    enabled: bool = True
    log_to_file: bool = True
    log_to_database: bool = True
    log_to_console: bool = False
    
    # File settings
    log_dir: str = "logs/audit"
    max_file_size_mb: int = 100
    retention_days: int = 90  # POPIA recommends keeping records
    
    # Filtering
    min_severity: EventSeverity = EventSeverity.DEBUG
    include_request_body: bool = False
    include_response_body: bool = False
    
    # POPIA settings
    anonymize_after_days: int = 365  # Anonymize personal data after 1 year
    encrypt_sensitive_fields: bool = True
    
    # Performance
    async_write: bool = True
    batch_size: int = 100
    flush_interval_seconds: int = 30
    
    @classmethod
    def from_env(cls, env_dict: Dict[str, Any]) -> "AuditLogConfig":
        """Create config from environment variables."""
        return cls(
            enabled=env_dict.get("AUDIT_LOG_ENABLED", "true").lower() == "true",
            log_to_file=env_dict.get("AUDIT_LOG_FILE", "true").lower() == "true",
            log_to_database=env_dict.get("AUDIT_LOG_DB", "true").lower() == "true",
            log_to_console=env_dict.get("AUDIT_LOG_CONSOLE", "false").lower() == "true",
            log_dir=env_dict.get("AUDIT_LOG_DIR", "logs/audit"),
            retention_days=int(env_dict.get("AUDIT_RETENTION_DAYS", "90")),
            anonymize_after_days=int(env_dict.get("AUDIT_ANONYMIZE_DAYS", "365")),
        )


class AuditLogger:
    """
    Comprehensive audit logger for RefurbAdmin AI.
    
    Features:
    - Thread-safe logging
    - File and database storage
    - POPIA compliance
    - Event filtering and search
    - Integrity verification
    """
    
    def __init__(self, config: Optional[AuditLogConfig] = None):
        self.config = config or AuditLogConfig()
        self._lock = threading.Lock()
        self._buffer: deque = deque(maxlen=1000)
        self._event_counter = 0
        
        # Setup file handler
        if self.config.log_to_file:
            self._setup_file_handler()
        
        # Setup database (lazy initialization)
        self._db_session = None
        
        logger.info("Audit logger initialized")
    
    def _setup_file_handler(self):
        """Setup file handler for audit logs."""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dedicated audit logger
        self._file_logger = logging.getLogger("audit")
        self._file_logger.setLevel(logging.DEBUG)
        self._file_logger.propagate = False
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            log_dir / "audit.log",
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=10
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self._file_logger.addHandler(handler)
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        with self._lock:
            self._event_counter += 1
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            return f"AUD-{timestamp}-{self._event_counter:06d}"
    
    def log(
        self,
        event_type: AuditEventType,
        severity: EventSeverity = EventSeverity.INFO,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        request_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        status_code: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        popia_purpose: Optional[str] = None,
        popia_data_subject: Optional[str] = None,
        popia_consent_obtained: bool = False,
        popia_retention_period: Optional[str] = None,
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (see AuditEventType)
            severity: Severity level
            user_*: User information
            ip_address: Client IP address
            user_agent: Client user agent
            endpoint: API endpoint accessed
            method: HTTP method
            request_id: Unique request identifier
            resource_*: Resource being accessed
            action: Action performed
            status: Success or failure
            status_code: HTTP status code
            metadata: Additional context
            popia_*: POPIA compliance fields
            
        Returns:
            The created AuditEvent
        """
        if not self.config.enabled:
            return None
        
        # Check severity filter
        severity_order = {
            EventSeverity.DEBUG: 0,
            EventSeverity.INFO: 1,
            EventSeverity.WARNING: 2,
            EventSeverity.ERROR: 3,
            EventSeverity.CRITICAL: 4,
        }
        
        if severity_order.get(severity, 0) < severity_order.get(self.config.min_severity, 0):
            return None
        
        # Create event
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type.value,
            timestamp=datetime.utcnow().isoformat(),
            severity=severity.value,
            user_id=user_id,
            user_email=self._hash_email(user_email) if user_email and self.config.encrypt_sensitive_fields else user_email,
            user_role=user_role,
            ip_address=self._mask_ip(ip_address) if ip_address else None,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            request_id=request_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            action=action,
            status=status,
            status_code=status_code,
            metadata=metadata or {},
            popia_purpose=popia_purpose,
            popia_data_subject=popia_data_subject,
            popia_consent_obtained=popia_consent_obtained,
            popia_retention_period=popia_retention_period,
        )
        
        # Write event
        self._write_event(event)
        
        return event
    
    def _hash_email(self, email: str) -> str:
        """Hash email for privacy protection."""
        if not email:
            return None
        return f"{email[:2]}***@{email.split('@')[1]}" if '@' in email else "***"
    
    def _mask_ip(self, ip: str) -> str:
        """Mask IP address for privacy."""
        if not ip:
            return None
        if ':' in ip:  # IPv6
            return ip[:4] + "::***"
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.***"
        return "***"
    
    def _write_event(self, event: AuditEvent):
        """Write event to all configured outputs."""
        # Add to buffer
        self._buffer.append(event)
        
        # Write to file
        if self.config.log_to_file and hasattr(self, '_file_logger'):
            self._write_to_file(event)
        
        # Write to database (if configured)
        if self.config.log_to_database:
            self._write_to_database(event)
        
        # Write to console (for debugging)
        if self.config.log_to_console:
            self._write_to_console(event)
    
    def _write_to_file(self, event: AuditEvent):
        """Write event to audit log file."""
        self._file_logger.info(event.to_json())
    
    def _write_to_database(self, event: AuditEvent):
        """Write event to database."""
        # Lazy database initialization
        if self._db_session is None:
            try:
                self._init_database()
            except Exception as e:
                logger.warning(f"Failed to initialize audit database: {e}")
                return
        
        # Insert event (implementation depends on your ORM)
        # This is a placeholder - implement based on your database setup
        pass
    
    def _init_database(self):
        """Initialize database connection for audit logs."""
        # Placeholder - implement based on your database setup
        # Example with SQLAlchemy:
        # from sqlalchemy.orm import sessionmaker
        # from app.database import engine
        # Session = sessionmaker(bind=engine)
        # self._db_session = Session()
        pass
    
    def _write_to_console(self, event: AuditEvent):
        """Write event to console."""
        print(f"[AUDIT] {event.event_type}: {event.event_id}")
    
    def log_api_request(
        self,
        request: Any,
        response: Any = None,
        duration_ms: float = 0,
        **kwargs
    ) -> AuditEvent:
        """
        Log an API request.
        
        Args:
            request: The incoming request object
            response: The response object (optional)
            duration_ms: Request duration in milliseconds
        """
        # Extract information from request
        # This is a generic implementation - adapt to your framework
        
        return self.log(
            event_type=AuditEventType.API_REQUEST,
            severity=EventSeverity.DEBUG,
            endpoint=getattr(request, 'url', {}).get('path') if hasattr(request, 'url') else None,
            method=getattr(request, 'method', None),
            ip_address=getattr(request, 'client', {}).get('host') if hasattr(request, 'client') else None,
            user_agent=getattr(request, 'headers', {}).get('user-agent') if hasattr(request, 'headers') else None,
            request_id=getattr(request, 'headers', {}).get('x-request-id') if hasattr(request, 'headers') else None,
            status_code=getattr(response, 'status_code', None),
            metadata={
                "duration_ms": duration_ms,
            },
            **kwargs
        )
    
    def log_auth_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        user_email: str,
        success: bool,
        ip_address: str = None,
        details: Dict[str, Any] = None,
    ) -> AuditEvent:
        """
        Log an authentication event.
        
        Args:
            event_type: AUTH_LOGIN_SUCCESS, AUTH_LOGIN_FAILED, etc.
            user_id: User ID
            user_email: User email
            success: Whether authentication succeeded
            ip_address: Client IP
            details: Additional details
        """
        severity = EventSeverity.INFO if success else EventSeverity.WARNING
        
        return self.log(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            status="success" if success else "failed",
            metadata=details or {},
        )
    
    def log_data_access(
        self,
        action: str,  # read, create, update, delete
        resource_type: str,
        resource_id: str,
        user_id: str,
        user_email: str = None,
        ip_address: str = None,
        popia_purpose: str = None,
        popia_consent_obtained: bool = False,
    ) -> AuditEvent:
        """
        Log data access for POPIA compliance.
        
        Args:
            action: The action performed (read, create, update, delete)
            resource_type: Type of resource accessed
            resource_id: ID of the resource
            user_id: User who performed the action
            user_email: User's email
            ip_address: Client IP
            popia_purpose: Purpose of data processing
            popia_consent_obtained: Whether consent was obtained
        """
        event_type_map = {
            "read": AuditEventType.DATA_READ,
            "create": AuditEventType.DATA_CREATE,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
        }
        
        return self.log(
            event_type=event_type_map.get(action, AuditEventType.DATA_READ),
            severity=EventSeverity.INFO,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            popia_purpose=popia_purpose,
            popia_consent_obtained=popia_consent_obtained,
        )
    
    def log_popia_event(
        self,
        event_type: AuditEventType,
        data_subject: str,
        user_id: str,
        details: Dict[str, Any] = None,
    ) -> AuditEvent:
        """
        Log POPIA-specific events.
        
        Args:
            event_type: POPPIA_CONSENT_GRANTED, POPPIA_DATA_ACCESS_REQUEST, etc.
            data_subject: The data subject (person)
            user_id: User who performed the action
            details: Additional details
        """
        return self.log(
            event_type=event_type,
            severity=EventSeverity.INFO,
            user_id=user_id,
            popia_data_subject=data_subject,
            popia_consent_obtained=True,
            metadata=details or {},
        )
    
    def log_security_event(
        self,
        event_type: AuditEventType,
        ip_address: str,
        details: Dict[str, Any] = None,
        severity: EventSeverity = EventSeverity.WARNING,
    ) -> AuditEvent:
        """
        Log security events.
        
        Args:
            event_type: SECURITY_VIOLATION, SECURITY_SQL_INJECTION, etc.
            ip_address: Source IP address
            details: Additional details
            severity: Event severity
        """
        return self.log(
            event_type=event_type,
            severity=severity,
            ip_address=ip_address,
            status="blocked",
            metadata=details or {},
        )
    
    def search_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[EventSeverity] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        Search audit events.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            resource_type: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date
            severity: Filter by severity
            limit: Maximum results to return
            
        Returns:
            List of matching AuditEvents
        """
        results = []
        
        for event in self._buffer:
            # Apply filters
            if event_type and event.event_type != event_type.value:
                continue
            if user_id and event.user_id != user_id:
                continue
            if resource_type and event.resource_type != resource_type:
                continue
            if severity and event.severity != severity.value:
                continue
            
            if start_date:
                event_date = datetime.fromisoformat(event.timestamp)
                if event_date < start_date:
                    continue
            
            if end_date:
                event_date = datetime.fromisoformat(event.timestamp)
                if event_date > end_date:
                    continue
            
            results.append(event)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_events_for_user(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get all events for a specific user."""
        return self.search_events(user_id=user_id, limit=limit)
    
    def get_events_for_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get all events for a specific resource."""
        return self.search_events(
            resource_type=resource_type,
            limit=limit
        )
    
    def export_events(
        self,
        output_path: str,
        format: str = "json",
        **search_kwargs
    ) -> str:
        """
        Export audit events to file.
        
        Args:
            output_path: Path to output file
            format: Output format (json, csv)
            **search_kwargs: Search parameters
            
        Returns:
            Path to exported file
        """
        events = self.search_events(**search_kwargs, limit=10000)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            with open(output_file, 'w') as f:
                json.dump([e.to_dict() for e in events], f, indent=2, default=str)
        elif format == "csv":
            import csv
            with open(output_file, 'w', newline='') as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=events[0].to_dict().keys())
                    writer.writeheader()
                    for event in events:
                        writer.writerow(event.to_dict())
        
        logger.info(f"Exported {len(events)} events to {output_path}")
        return str(output_file)
    
    def anonymize_old_events(self, days_old: int = None) -> int:
        """
        Anonymize personal data in old events for POPIA compliance.
        
        Args:
            days_old: Anonymize events older than this many days
            
        Returns:
            Number of events anonymized
        """
        if days_old is None:
            days_old = self.config.anonymize_after_days
        
        cutoff = datetime.utcnow()
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days_old)
        
        count = 0
        for event in self._buffer:
            event_date = datetime.fromisoformat(event.timestamp)
            if event_date < cutoff:
                # Anonymize personal data
                event.user_email = "***anonymized***"
                event.user_id = None
                event.ip_address = None
                count += 1
        
        logger.info(f"Anonymized {count} events older than {days_old} days")
        return count
    
    def flush(self):
        """Flush buffered events to storage."""
        # Implementation for batch writing
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        event_types = {}
        severities = {}
        
        for event in self._buffer:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            severities[event.severity] = severities.get(event.severity, 0) + 1
        
        return {
            "total_events": len(self._buffer),
            "event_types": event_types,
            "severities": severities,
            "config": {
                "enabled": self.config.enabled,
                "retention_days": self.config.retention_days,
                "anonymize_after_days": self.config.anonymize_after_days,
            }
        }


# Singleton instance
_audit_logger_instance: Optional[AuditLogger] = None


def get_audit_logger(config: Optional[AuditLogConfig] = None) -> AuditLogger:
    """Get or create the audit logger singleton."""
    global _audit_logger_instance
    
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger(config=config)
    
    return _audit_logger_instance


# FastAPI middleware
class AuditMiddleware:
    """
    FastAPI middleware for automatic audit logging.
    
    Usage:
        app.add_middleware(AuditMiddleware, audit_logger=audit_logger)
    """
    
    def __init__(self, app, audit_logger: AuditLogger):
        self.app = app
        self.audit_logger = audit_logger
    
    async def __call__(self, scope, receive, send):
        import time
        from fastapi import Request
        
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        start_time = time.time()
        request = Request(scope, receive)
        
        # Process request
        response = await self.app(scope, receive, send)
        
        # Log request
        duration_ms = (time.time() - start_time) * 1000
        
        self.audit_logger.log_api_request(
            request=request,
            duration_ms=duration_ms,
        )
        
        return response
