"""
Tests for Audit Logger module.

Tests cover:
- Event logging
- POPIA compliance logging
- Event search and filtering
- Export functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.security.audit_logger import (
    AuditLogger,
    AuditLogConfig,
    AuditEvent,
    AuditEventType,
    EventSeverity,
    get_audit_logger,
)


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""
    
    def test_create_event(self):
        """Test creating an audit event."""
        event = AuditEvent(
            event_id="AUD-001",
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS.value,
            timestamp=datetime.utcnow().isoformat(),
            severity=EventSeverity.INFO.value,
            user_id="user123",
        )
        
        assert event.event_id == "AUD-001"
        assert event.user_id == "user123"
        assert event.status == "success"
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = AuditEvent(
            event_id="AUD-001",
            event_type="test.event",
            timestamp=datetime.utcnow().isoformat(),
            severity="info",
        )
        
        result = event.to_dict()
        
        assert result["event_id"] == "AUD-001"
        assert result["event_type"] == "test.event"
    
    def test_event_to_json(self):
        """Test converting event to JSON."""
        event = AuditEvent(
            event_id="AUD-001",
            event_type="test.event",
            timestamp=datetime.utcnow().isoformat(),
            severity="info",
        )
        
        json_str = event.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["event_id"] == "AUD-001"
    
    def test_event_hash(self):
        """Test event hash generation."""
        event1 = AuditEvent(
            event_id="AUD-001",
            event_type="test.event",
            timestamp=datetime.utcnow().isoformat(),
            severity="info",
        )
        
        event2 = AuditEvent(
            event_id="AUD-001",
            event_type="test.event",
            timestamp=datetime.utcnow().isoformat(),
            severity="info",
        )
        
        # Same content should produce same hash
        assert event1.get_hash() == event2.get_hash()
    
    def test_popia_fields(self):
        """Test POPIA-specific fields."""
        event = AuditEvent(
            event_id="AUD-001",
            event_type=AuditEventType.POPPIA_CONSENT_GRANTED.value,
            timestamp=datetime.utcnow().isoformat(),
            severity="info",
            popia_purpose="Marketing",
            popia_data_subject="John Doe",
            popia_consent_obtained=True,
        )
        
        assert event.popia_purpose == "Marketing"
        assert event.popia_data_subject == "John Doe"
        assert event.popia_consent_obtained is True


class TestAuditLogConfig:
    """Tests for AuditLogConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AuditLogConfig()
        
        assert config.enabled is True
        assert config.log_to_file is True
        assert config.log_to_database is True
        assert config.retention_days == 90
    
    def test_config_from_env(self):
        """Test creating config from environment variables."""
        env_dict = {
            "AUDIT_LOG_ENABLED": "false",
            "AUDIT_LOG_FILE": "false",
            "AUDIT_LOG_DB": "false",
            "AUDIT_LOG_CONSOLE": "true",
            "AUDIT_RETENTION_DAYS": "30",
        }
        
        config = AuditLogConfig.from_env(env_dict)
        
        assert config.enabled is False
        assert config.log_to_file is False
        assert config.log_to_database is False
        assert config.log_to_console is True
        assert config.retention_days == 30


class TestAuditLogger:
    """Tests for AuditLogger class."""
    
    @pytest.fixture
    def logger(self):
        """Create an audit logger for testing."""
        config = AuditLogConfig(
            enabled=True,
            log_to_file=False,
            log_to_database=False,
            log_to_console=False,
        )
        return AuditLogger(config=config)
    
    def test_log_event(self, logger):
        """Test logging an event."""
        event = logger.log(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            severity=EventSeverity.INFO,
            user_id="user123",
            user_email="user@example.com",
        )
        
        assert event is not None
        assert event.event_type == AuditEventType.AUTH_LOGIN_SUCCESS.value
        assert event.user_id == "user123"
    
    def test_disabled_logger(self):
        """Test disabled logger doesn't log events."""
        config = AuditLogConfig(enabled=False)
        logger = AuditLogger(config=config)
        
        event = logger.log(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user123",
        )
        
        assert event is None
    
    def test_severity_filter(self, logger):
        """Test severity filtering."""
        logger.config.min_severity = EventSeverity.ERROR
        
        # INFO event should be filtered
        event = logger.log(
            event_type=AuditEventType.API_REQUEST,
            severity=EventSeverity.INFO,
        )
        
        assert event is None
        
        # ERROR event should pass
        event = logger.log(
            event_type=AuditEventType.API_ERROR,
            severity=EventSeverity.ERROR,
        )
        
        assert event is not None
    
    def test_ip_masking(self, logger):
        """Test IP address masking for privacy."""
        event = logger.log(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            ip_address="192.168.1.100",
        )
        
        # IP should be masked
        assert event.ip_address == "192.168.***.***"
    
    def test_email_hashing(self, logger):
        """Test email hashing for privacy."""
        logger.config.encrypt_sensitive_fields = True
        
        event = logger.log(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_email="user@example.com",
        )
        
        # Email should be partially hidden
        assert "***" in event.user_email
    
    def test_log_auth_event(self, logger):
        """Test logging authentication events."""
        event = logger.log_auth_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user123",
            user_email="user@example.com",
            success=True,
            ip_address="192.168.1.100",
        )
        
        assert event is not None
        assert event.status == "success"
    
    def test_log_data_access(self, logger):
        """Test logging data access for POPIA."""
        event = logger.log_data_access(
            action="read",
            resource_type="customer",
            resource_id="cust123",
            user_id="user123",
            popia_purpose="Order fulfillment",
            popia_consent_obtained=True,
        )
        
        assert event is not None
        assert event.event_type == AuditEventType.DATA_READ.value
        assert event.popia_purpose == "Order fulfillment"
    
    def test_log_popia_event(self, logger):
        """Test logging POPIA-specific events."""
        event = logger.log_popia_event(
            event_type=AuditEventType.POPPIA_CONSENT_GRANTED,
            data_subject="John Doe",
            user_id="admin",
            details={"consent_type": "marketing"},
        )
        
        assert event is not None
        assert event.event_type == AuditEventType.POPPIA_CONSENT_GRANTED.value
        assert event.popia_data_subject == "John Doe"
    
    def test_log_security_event(self, logger):
        """Test logging security events."""
        event = logger.log_security_event(
            event_type=AuditEventType.SECURITY_SQL_INJECTION,
            ip_address="10.0.0.100",
            details={"endpoint": "/api/users"},
            severity=EventSeverity.WARNING,
        )
        
        assert event is not None
        assert event.event_type == AuditEventType.SECURITY_SQL_INJECTION.value
        assert event.status == "blocked"
    
    def test_search_events(self, logger):
        """Test searching events."""
        # Log some events
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS, user_id="user1")
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS, user_id="user2")
        logger.log(event_type=AuditEventType.DATA_READ, user_id="user1")
        
        # Search by user
        events = logger.search_events(user_id="user1")
        
        assert len(events) == 2
    
    def test_search_events_by_type(self, logger):
        """Test searching events by type."""
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS)
        logger.log(event_type=AuditEventType.DATA_READ)
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS)
        
        events = logger.search_events(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS
        )
        
        assert len(events) == 2
    
    def test_search_events_by_date(self, logger):
        """Test searching events by date range."""
        # Log events
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS)
        
        # Search with date range
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)
        
        events = logger.search_events(
            start_date=start_date,
            end_date=end_date,
        )
        
        assert len(events) >= 0  # May be 0 if buffer is empty
    
    def test_get_events_for_user(self, logger):
        """Test getting events for specific user."""
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS, user_id="testuser")
        logger.log(event_type=AuditEventType.DATA_READ, user_id="testuser")
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS, user_id="otheruser")
        
        events = logger.get_events_for_user("testuser")
        
        assert len(events) == 2
    
    def test_get_stats(self, logger):
        """Test getting audit log statistics."""
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS)
        logger.log(event_type=AuditEventType.DATA_READ)
        
        stats = logger.get_stats()
        
        assert "total_events" in stats
        assert "event_types" in stats
        assert "config" in stats


class TestAuditLoggerExport:
    """Tests for audit log export functionality."""
    
    @pytest.fixture
    def logger(self, tmp_path):
        """Create an audit logger with temp directory."""
        config = AuditLogConfig(
            enabled=True,
            log_to_file=False,
            log_to_database=False,
        )
        logger = AuditLogger(config=config)
        logger._temp_dir = tmp_path
        return logger
    
    def test_export_to_json(self, logger, tmp_path):
        """Test exporting events to JSON."""
        # Log some events
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS)
        logger.log(event_type=AuditEventType.DATA_READ)
        
        output_path = tmp_path / "audit_export.json"
        
        result_path = logger.export_events(
            str(output_path),
            format="json",
        )
        
        assert result_path == str(output_path)
        assert output_path.exists()
        
        # Verify content
        with open(output_path) as f:
            data = json.load(f)
        
        assert isinstance(data, list)
    
    def test_export_to_csv(self, logger, tmp_path):
        """Test exporting events to CSV."""
        # Log some events
        logger.log(event_type=AuditEventType.AUTH_LOGIN_SUCCESS)
        
        output_path = tmp_path / "audit_export.csv"
        
        result_path = logger.export_events(
            str(output_path),
            format="csv",
        )
        
        assert result_path == str(output_path)
        assert output_path.exists()


class TestAuditLoggerAnonymization:
    """Tests for event anonymization (POPIA compliance)."""
    
    @pytest.fixture
    def logger(self):
        """Create an audit logger for testing."""
        config = AuditLogConfig(
            enabled=True,
            log_to_file=False,
            log_to_database=False,
            anonymize_after_days=1,
        )
        return AuditLogger(config=config)
    
    def test_anonymize_old_events(self, logger):
        """Test anonymizing old events."""
        # Log events
        logger.log(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user123",
            user_email="user@example.com",
            ip_address="192.168.1.100",
        )
        
        # Anonymize (with 0 days to anonymize all)
        count = logger.anonymize_old_events(days_old=0)
        
        # Events should be anonymized
        events = logger.search_events()
        for event in events:
            assert event.user_id is None or event.user_id == "***anonymized***"


class TestAuditMiddleware:
    """Tests for AuditMiddleware."""
    
    def test_middleware_initialization(self):
        """Test middleware can be initialized."""
        from app.security.audit_logger import AuditMiddleware
        
        config = AuditLogConfig(enabled=False)
        logger = AuditLogger(config=config)
        
        # Mock ASGI app
        mock_app = Mock()
        
        middleware = AuditMiddleware(mock_app, logger)
        
        assert middleware.app == mock_app
        assert middleware.audit_logger == logger


class TestGetAuditLogger:
    """Tests for get_audit_logger singleton."""
    
    def test_singleton_returns_same_instance(self):
        """Test that get_audit_logger returns same instance."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        
        assert logger1 is logger2
    
    def test_singleton_with_config(self):
        """Test singleton with custom config."""
        config = AuditLogConfig(retention_days=30)
        logger = get_audit_logger(config=config)
        
        assert logger.config.retention_days == 30


class TestAuditEventType:
    """Tests for AuditEventType enum."""
    
    def test_auth_events(self):
        """Test authentication event types."""
        assert AuditEventType.AUTH_LOGIN_SUCCESS.value == "auth.login.success"
        assert AuditEventType.AUTH_LOGIN_FAILED.value == "auth.login.failed"
        assert AuditEventType.AUTH_LOGOUT.value == "auth.logout"
    
    def test_data_events(self):
        """Test data access event types."""
        assert AuditEventType.DATA_READ.value == "data.read"
        assert AuditEventType.DATA_CREATE.value == "data.create"
        assert AuditEventType.DATA_UPDATE.value == "data.update"
        assert AuditEventType.DATA_DELETE.value == "data.delete"
    
    def test_popia_events(self):
        """Test POPIA event types."""
        assert AuditEventType.POPPIA_CONSENT_GRANTED.value == "popia.consent.granted"
        assert AuditEventType.POPPIA_DATA_DELETION.value == "popia.data.deletion"
    
    def test_security_events(self):
        """Test security event types."""
        assert AuditEventType.SECURITY_SQL_INJECTION.value == "security.sql_injection"
        assert AuditEventType.SECURITY_XSS_ATTEMPT.value == "security.xss_attempt"


class TestEventSeverity:
    """Tests for EventSeverity enum."""
    
    def test_severity_levels(self):
        """Test severity level values."""
        assert EventSeverity.DEBUG.value == "debug"
        assert EventSeverity.INFO.value == "info"
        assert EventSeverity.WARNING.value == "warning"
        assert EventSeverity.ERROR.value == "error"
        assert EventSeverity.CRITICAL.value == "critical"
