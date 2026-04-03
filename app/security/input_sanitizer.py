"""
Input Sanitizer for RefurbAdmin AI.

Provides comprehensive input validation and sanitization:
- SQL injection prevention
- XSS (Cross-Site Scripting) prevention
- Path traversal prevention
- Serial number validation (South African format support)
- Email and phone number validation

OWASP compliant with POPIA considerations for personal data.
"""

import re
import os
import html
import logging
from typing import Optional, Any, Dict, List, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class SanitizationLevel(Enum):
    """Levels of input sanitization."""
    MINIMAL = "minimal"      # Basic escaping only
    STANDARD = "standard"    # Standard security sanitization
    STRICT = "strict"        # Strict validation, alphanumeric only
    CUSTOM = "custom"        # Custom rules


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    
    original: Any
    sanitized: Any
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self) -> bool:
        return self.is_valid


# SQL Injection patterns (OWASP)
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
    r"(--|#|\/\*)",  # SQL comments
    r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",  # OR 1=1, AND 1=1
    r"(\b(OR|AND)\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",  # OR 'a'='a'
    r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))",  # Stacked queries
    r"(\bEXEC(\UTE)?\b)",  # EXEC/EXECUTE
    r"(\b(WAITFOR|BENCHMARK|SLEEP)\b)",  # Time-based injection
    r"(\b(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)\b)",  # System tables
]

# XSS patterns
XSS_PATTERNS = [
    r"<\s*script",  # Script tags
    r"javascript\s*:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers (onclick, onerror, etc.)
    r"<\s*img[^>]+onerror",  # Image onerror
    r"<\s*svg[^>]+onload",  # SVG onload
    r"<\s*iframe",  # iframe tags
    r"<\s*object",  # object tags
    r"<\s*embed",  # embed tags
    r"<\s*link[^>]+href\s*=\s*['\"]?javascript",  # Link with javascript
    r"expression\s*\(",  # CSS expression
    r"url\s*\(\s*['\"]?javascript",  # CSS url with javascript
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",  # Basic parent directory
    r"\.\.\\",  # Windows parent directory
    r"%2e%2e%2f",  # URL encoded ../
    r"%2e%2e/",  # Partial URL encoded
    r"\.\.%2f",  # Partial URL encoded
    r"%2e%2e\\",  # URL encoded ..\
    r"\.\.%5c",  # Partial URL encoded
    r"%252e%252e%252f",  # Double URL encoded
    r"/etc/passwd",  # Linux sensitive files
    r"/etc/shadow",  # Linux sensitive files
    r"c:\\windows",  # Windows sensitive paths
    r"c:/windows",  # Windows sensitive paths
]


class InputSanitizer:
    """
    Comprehensive input sanitizer for RefurbAdmin AI.
    
    Provides protection against:
    - SQL Injection
    - Cross-Site Scripting (XSS)
    - Path Traversal attacks
    - Invalid serial numbers
    - Malformed emails and phone numbers
    """
    
    def __init__(
        self,
        level: SanitizationLevel = SanitizationLevel.STANDARD,
        allow_unicode: bool = True,
        max_length: int = 10000
    ):
        self.level = level
        self.allow_unicode = allow_unicode
        self.max_length = max_length
        
        # Compile regex patterns for performance
        self._sql_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in SQL_INJECTION_PATTERNS
        ]
        self._xss_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in XSS_PATTERNS
        ]
        self._path_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in PATH_TRAVERSAL_PATTERNS
        ]
        
        # South African phone number patterns
        self._sa_phone_patterns = [
            re.compile(r"^\+27\d{9}$"),  # +27XXXXXXXXX
            re.compile(r"^0\d{9}$"),  # 0XXXXXXXXX
            re.compile(r"^\d{10}$"),  # XXXXXXXXXX
        ]
        
        # Email pattern (RFC 5322 simplified)
        self._email_pattern = re.compile(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        
        # South African ID number pattern (13 digits)
        self._sa_id_pattern = re.compile(r"^\d{13}$")
        
        # Serial number patterns (common formats)
        self._serial_patterns = [
            re.compile(r"^[A-Z0-9]{8,20}$"),  # Alphanumeric
            re.compile(r"^[A-Z]{2,4}-\d{6,10}$"),  # XX-123456 format
            re.compile(r"^[A-Z]\d{10}$"),  # RefurbAdmin format
        ]
    
    def sanitize(
        self,
        value: Any,
        field_name: str = "input",
        custom_rules: Optional[Dict[str, Any]] = None
    ) -> SanitizationResult:
        """
        Sanitize input value.
        
        Args:
            value: The value to sanitize
            field_name: Name of the field for error messages
            custom_rules: Optional custom validation rules
            
        Returns:
            SanitizationResult with sanitized value and validation status
        """
        errors = []
        warnings = []
        
        # Handle None
        if value is None:
            return SanitizationResult(
                original=value,
                sanitized=None,
                is_valid=True,
                errors=[],
                warnings=[]
            )
        
        # Handle non-string types
        if not isinstance(value, str):
            if isinstance(value, (int, float, bool)):
                return SanitizationResult(
                    original=value,
                    sanitized=value,
                    is_valid=True,
                    errors=[],
                    warnings=[]
                )
            elif isinstance(value, (list, tuple)):
                return self._sanitize_list(value, field_name)
            elif isinstance(value, dict):
                return self._sanitize_dict(value, field_name)
            else:
                # Convert to string for sanitization
                value = str(value)
                warnings.append(f"Converted {type(value).__name__} to string")
        
        # Check max length
        if len(value) > self.max_length:
            errors.append(f"{field_name} exceeds maximum length of {self.max_length}")
            return SanitizationResult(
                original=value,
                sanitized=None,
                is_valid=False,
                errors=errors,
                warnings=warnings
            )
        
        sanitized = value
        
        # Apply sanitization based on level
        if self.level == SanitizationLevel.STRICT:
            sanitized = self._strict_sanitize(sanitized)
        elif self.level == SanitizationLevel.STANDARD:
            sanitized = self._standard_sanitize(sanitized)
        elif self.level == SanitizationLevel.MINIMAL:
            sanitized = self._minimal_sanitize(sanitized)
        
        # Check for SQL injection
        sql_detected = self._check_sql_injection(sanitized)
        if sql_detected:
            errors.append(f"Potential SQL injection detected in {field_name}")
            logger.warning(f"SQL injection attempt detected: {field_name}")
        
        # Check for XSS
        xss_detected = self._check_xss(sanitized)
        if xss_detected:
            errors.append(f"Potential XSS attack detected in {field_name}")
            logger.warning(f"XSS attempt detected: {field_name}")
        
        # Check for path traversal
        path_detected = self._check_path_traversal(sanitized)
        if path_detected:
            errors.append(f"Potential path traversal detected in {field_name}")
            logger.warning(f"Path traversal attempt detected: {field_name}")
        
        # Apply custom rules if provided
        if custom_rules:
            custom_result = self._apply_custom_rules(
                sanitized, field_name, custom_rules
            )
            errors.extend(custom_result.errors)
            warnings.extend(custom_result.warnings)
            if not custom_result.is_valid:
                sanitized = None
        
        is_valid = len(errors) == 0
        
        return SanitizationResult(
            original=value,
            sanitized=sanitized if is_valid else None,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    def _minimal_sanitize(self, value: str) -> str:
        """Minimal sanitization - basic HTML escaping."""
        return html.escape(value, quote=True)
    
    def _standard_sanitize(self, value: str) -> str:
        """Standard sanitization - HTML escaping and null byte removal."""
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove control characters except newline and tab
        value = ''.join(
            char for char in value 
            if ord(char) >= 32 or char in '\n\t\r'
        )
        
        # HTML escape
        value = html.escape(value, quote=True)
        
        return value
    
    def _strict_sanitize(self, value: str) -> str:
        """Strict sanitization - alphanumeric only."""
        # Remove all non-alphanumeric characters
        if self.allow_unicode:
            # Allow unicode letters and numbers
            return ''.join(
                char for char in value 
                if char.isalnum() or char in ' _-'
            )
        else:
            # ASCII alphanumeric only
            return re.sub(r'[^a-zA-Z0-9 _-]', '', value)
    
    def _sanitize_list(
        self, 
        value: Union[List, Tuple], 
        field_name: str
    ) -> SanitizationResult:
        """Sanitize list/tuple values."""
        results = []
        all_valid = True
        all_errors = []
        all_warnings = []
        
        for i, item in enumerate(value):
            result = self.sanitize(item, f"{field_name}[{i}]")
            results.append(result.sanitized)
            all_valid = all_valid and result.is_valid
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        return SanitizationResult(
            original=value,
            sanitized=results if all_valid else None,
            is_valid=all_valid,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def _sanitize_dict(self, value: Dict, field_name: str) -> SanitizationResult:
        """Sanitize dictionary values."""
        results = {}
        all_valid = True
        all_errors = []
        all_warnings = []
        
        for key, val in value.items():
            # Sanitize keys (should be strings)
            key_result = self.sanitize(str(key), f"{field_name}.key")
            if not key_result.is_valid:
                all_valid = False
                all_errors.extend(key_result.errors)
                continue
            
            # Sanitize values
            val_result = self.sanitize(val, f"{field_name}.{key}")
            results[key_result.sanitized] = val_result.sanitized
            all_valid = all_valid and val_result.is_valid
            all_errors.extend(val_result.errors)
            all_warnings.extend(val_result.warnings)
        
        return SanitizationResult(
            original=value,
            sanitized=results if all_valid else None,
            is_valid=all_valid,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def _check_sql_injection(self, value: str) -> bool:
        """Check for SQL injection patterns."""
        for pattern in self._sql_patterns:
            if pattern.search(value):
                return True
        return False
    
    def _check_xss(self, value: str) -> bool:
        """Check for XSS patterns."""
        for pattern in self._xss_patterns:
            if pattern.search(value):
                return True
        return False
    
    def _check_path_traversal(self, value: str) -> bool:
        """Check for path traversal patterns."""
        # Check URL decoded version too
        from urllib.parse import unquote
        decoded_value = unquote(value)
        
        for pattern in self._path_patterns:
            if pattern.search(value) or pattern.search(decoded_value):
                return True
        return False
    
    def _apply_custom_rules(
        self,
        value: str,
        field_name: str,
        rules: Dict[str, Any]
    ) -> SanitizationResult:
        """Apply custom validation rules."""
        errors = []
        warnings = []
        
        # Min length
        if "min_length" in rules:
            if len(value) < rules["min_length"]:
                errors.append(
                    f"{field_name} must be at least {rules['min_length']} characters"
                )
        
        # Max length
        if "max_length" in rules:
            if len(value) > rules["max_length"]:
                errors.append(
                    f"{field_name} must be at most {rules['max_length']} characters"
                )
        
        # Pattern matching
        if "pattern" in rules:
            pattern = re.compile(rules["pattern"])
            if not pattern.match(value):
                errors.append(f"{field_name} does not match required pattern")
        
        # Allowed values
        if "allowed_values" in rules:
            if value not in rules["allowed_values"]:
                errors.append(
                    f"{field_name} must be one of: {rules['allowed_values']}"
                )
        
        return SanitizationResult(
            original=value,
            sanitized=value,
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    # === Specialized Validators ===
    
    def validate_serial_number(
        self,
        serial: str,
        format_type: str = "standard"
    ) -> SanitizationResult:
        """
        Validate serial number format.
        
        Args:
            serial: The serial number to validate
            format_type: One of 'standard', 'refurbadmin', 'custom'
            
        Returns:
            SanitizationResult with validation status
        """
        errors = []
        warnings = []
        
        if not serial:
            return SanitizationResult(
                original=serial,
                sanitized=None,
                is_valid=False,
                errors=["Serial number is required"],
                warnings=[]
            )
        
        # Clean the serial number
        serial = serial.strip().upper()
        
        # Check for suspicious patterns first
        if self._check_sql_injection(serial) or self._check_xss(serial):
            return SanitizationResult(
                original=serial,
                sanitized=None,
                is_valid=False,
                errors=["Invalid characters in serial number"],
                warnings=[]
            )
        
        # Validate based on format type
        is_valid = False
        
        if format_type == "standard":
            for pattern in self._serial_patterns:
                if pattern.match(serial):
                    is_valid = True
                    break
        elif format_type == "refurbadmin":
            # RefurbAdmin specific format: Letter + 10 digits
            if re.match(r"^[A-Z]\d{10}$", serial):
                is_valid = True
        elif format_type == "custom":
            # Accept any alphanumeric 6-25 chars
            if re.match(r"^[A-Z0-9]{6,25}$", serial):
                is_valid = True
        
        if not is_valid:
            errors.append(
                f"Invalid serial number format. Expected {format_type} format."
            )
        
        return SanitizationResult(
            original=serial,
            sanitized=serial if is_valid else None,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    def validate_email(self, email: str) -> SanitizationResult:
        """
        Validate email address format.
        
        Args:
            email: The email address to validate
            
        Returns:
            SanitizationResult with validation status
        """
        errors = []
        warnings = []
        
        if not email:
            return SanitizationResult(
                original=email,
                sanitized=None,
                is_valid=False,
                errors=["Email address is required"],
                warnings=[]
            )
        
        email = email.strip().lower()
        
        # Check length
        if len(email) > 254:
            errors.append("Email address too long (max 254 characters)")
            return SanitizationResult(
                original=email,
                sanitized=None,
                is_valid=False,
                errors=errors,
                warnings=[]
            )
        
        # Validate format
        if not self._email_pattern.match(email):
            errors.append("Invalid email address format")
            return SanitizationResult(
                original=email,
                sanitized=None,
                is_valid=False,
                errors=errors,
                warnings=[]
            )
        
        # Check for disposable email domains (common in SA)
        disposable_domains = [
            "tempmail.com", "throwaway.com", "guerrillamail.com"
        ]
        domain = email.split('@')[1]
        if domain in disposable_domains:
            warnings.append("Email from disposable email provider")
        
        return SanitizationResult(
            original=email,
            sanitized=email,
            is_valid=True,
            errors=[],
            warnings=warnings
        )
    
    def validate_phone(
        self,
        phone: str,
        country: str = "ZA"
    ) -> SanitizationResult:
        """
        Validate phone number format.
        
        Args:
            phone: The phone number to validate
            country: Country code ('ZA' for South Africa)
            
        Returns:
            SanitizationResult with validation status
        """
        errors = []
        warnings = []
        
        if not phone:
            return SanitizationResult(
                original=phone,
                sanitized=None,
                is_valid=False,
                errors=["Phone number is required"],
                warnings=[]
            )
        
        # Clean the phone number
        phone = phone.strip()
        
        # Remove common separators
        phone = re.sub(r'[\s\-\.\(\)]', '', phone)
        
        # Remove leading + or 00 for international
        if phone.startswith('+'):
            phone = phone[1:]
        elif phone.startswith('00'):
            phone = phone[2:]
        
        if country == "ZA":
            # South African phone validation
            # Format: +27XXXXXXXXX or 0XXXXXXXXX
            
            # Add country code if missing
            if phone.startswith('27'):
                normalized = f"+{phone}"
            elif phone.startswith('0'):
                normalized = f"+27{phone[1:]}"
            else:
                normalized = f"+27{phone}"
            
            # Validate format (10 digits after country code)
            digits_only = re.sub(r'\D', '', normalized)
            if len(digits_only) != 11:  # 27 + 9 digits
                errors.append(
                    "Invalid South African phone number. "
                    "Expected format: 0XXXXXXXXX or +27XXXXXXXXX"
                )
                return SanitizationResult(
                    original=phone,
                    sanitized=None,
                    is_valid=False,
                    errors=errors,
                    warnings=[]
                )
            
            # Validate mobile prefix (South African mobile networks)
            mobile_prefixes = ['60', '61', '62', '63', '64', '65', '70', '71', '72', 
                             '73', '74', '75', '76', '77', '78', '79', '80', '81', 
                             '82', '83', '84', '85', '86', '87', '88', '89']
            
            if digits_only[2:4] in mobile_prefixes:
                warnings.append("Mobile number detected")
            
            return SanitizationResult(
                original=phone,
                sanitized=normalized,
                is_valid=True,
                errors=[],
                warnings=warnings
            )
        else:
            # Generic international validation
            digits_only = re.sub(r'\D', '', phone)
            if len(digits_only) < 10 or len(digits_only) > 15:
                errors.append("Invalid phone number length")
                return SanitizationResult(
                    original=phone,
                    sanitized=None,
                    is_valid=False,
                    errors=errors,
                    warnings=[]
                )
            
            return SanitizationResult(
                original=phone,
                sanitized=f"+{digits_only}",
                is_valid=True,
                errors=[],
                warnings=[]
            )
    
    def validate_sa_id(self, id_number: str) -> SanitizationResult:
        """
        Validate South African ID number.
        
        Args:
            id_number: The SA ID number (13 digits)
            
        Returns:
            SanitizationResult with validation status
        """
        errors = []
        warnings = []
        
        if not id_number:
            return SanitizationResult(
                original=id_number,
                sanitized=None,
                is_valid=False,
                errors=["ID number is required"],
                warnings=[]
            )
        
        id_number = id_number.strip()
        
        # Check format (13 digits)
        if not self._sa_id_pattern.match(id_number):
            errors.append(
                "Invalid South African ID number format. "
                "Expected 13 digits (e.g., 8001015009087)"
            )
            return SanitizationResult(
                original=id_number,
                sanitized=None,
                is_valid=False,
                errors=errors,
                warnings=[]
            )
        
        # Validate checksum (Luhn algorithm variant)
        if not self._validate_sa_id_checksum(id_number):
            errors.append("Invalid ID number checksum")
            return SanitizationResult(
                original=id_number,
                sanitized=None,
                is_valid=False,
                errors=errors,
                warnings=[]
            )
        
        # Extract birthdate and validate
        try:
            year = int(id_number[0:2])
            month = int(id_number[2:4])
            day = int(id_number[4:6])
            
            # Determine century (SA ID uses 2-digit year)
            current_year = 2024
            if year > current_year % 100:
                full_year = 1900 + year
            else:
                full_year = 2000 + year
            
            # Basic date validation
            if month < 1 or month > 12:
                errors.append("Invalid month in ID number")
            if day < 1 or day > 31:
                errors.append("Invalid day in ID number")
        except ValueError:
            errors.append("Invalid date components in ID number")
        
        is_valid = len(errors) == 0
        
        return SanitizationResult(
            original=id_number,
            sanitized=id_number if is_valid else None,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_sa_id_checksum(self, id_number: str) -> bool:
        """
        Validate South African ID checksum.
        
        Uses a variant of the Luhn algorithm.
        """
        if len(id_number) != 13:
            return False
        
        try:
            digits = [int(d) for d in id_number]
        except ValueError:
            return False
        
        # SA ID checksum calculation
        total = 0
        for i in range(12):
            if i % 2 == 0:
                total += digits[i]
            else:
                doubled = digits[i] * 2
                total += doubled if doubled < 10 else doubled - 9
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == digits[12]
    
    def sanitize_path(self, path: str, base_dir: Optional[str] = None) -> SanitizationResult:
        """
        Sanitize file path and prevent path traversal.
        
        Args:
            path: The file path to sanitize
            base_dir: Base directory to restrict paths to
            
        Returns:
            SanitizationResult with sanitized path
        """
        errors = []
        warnings = []
        
        if not path:
            return SanitizationResult(
                original=path,
                sanitized=None,
                is_valid=False,
                errors=["Path is required"],
                warnings=[]
            )
        
        # Check for path traversal patterns
        if self._check_path_traversal(path):
            errors.append("Path traversal attempt detected")
            return SanitizationResult(
                original=path,
                sanitized=None,
                is_valid=False,
                errors=errors,
                warnings=[]
            )
        
        # Normalize path
        path = os.path.normpath(path)
        
        # If base_dir is provided, ensure path is within it
        if base_dir:
            base_dir = os.path.abspath(base_dir)
            full_path = os.path.abspath(os.path.join(base_dir, path))
            
            # Check if resolved path is within base directory
            if not full_path.startswith(base_dir):
                errors.append("Path escapes base directory")
                return SanitizationResult(
                    original=path,
                    sanitized=None,
                    is_valid=False,
                    errors=errors,
                    warnings=[]
                )
            
            path = os.path.relpath(full_path, base_dir)
        
        return SanitizationResult(
            original=path,
            sanitized=path,
            is_valid=True,
            errors=[],
            warnings=[]
        )


# Singleton instance
_sanitizer_instance: Optional[InputSanitizer] = None


def get_sanitizer(
    level: SanitizationLevel = SanitizationLevel.STANDARD
) -> InputSanitizer:
    """Get or create the sanitizer singleton."""
    global _sanitizer_instance
    
    if _sanitizer_instance is None:
        _sanitizer_instance = InputSanitizer(level=level)
    
    return _sanitizer_instance


# FastAPI dependency
def sanitize_input(
    value: str,
    field_name: str = "input"
) -> SanitizationResult:
    """FastAPI dependency for input sanitization."""
    sanitizer = get_sanitizer()
    return sanitizer.sanitize(value, field_name)
