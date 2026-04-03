"""
WhatsApp Service for RefurbAdmin AI.

Provides WhatsApp integration for South African customers:
- Quick quotes via WhatsApp
- Status updates
- Customer support
- South African phone number formatting

Supports:
- WhatsApp Business API
- Twilio WhatsApp API
- 360dialog
- Local SA WhatsApp Business providers
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WhatsAppMessageType(Enum):
    """WhatsApp message types."""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"


@dataclass
class WhatsAppConfig:
    """WhatsApp configuration."""
    
    # API settings
    enabled: bool = False
    provider: str = "twilio"  # twilio, 360dialog, meta
    api_key: str = ""
    api_url: str = ""
    phone_number_id: str = ""
    business_account_id: str = ""
    
    # WhatsApp Business API (Meta)
    whatsapp_business_phone_number: str = ""
    whatsapp_business_account_id: str = ""
    
    # Twilio settings
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    
    # Message settings
    from_number: str = ""
    default_template_language: str = "en"
    
    # Rate limiting
    rate_limit_per_minute: int = 80  # WhatsApp limit
    
    # South African settings
    country_code: str = "27"
    
    @classmethod
    def from_env(cls) -> "WhatsAppConfig":
        """Create config from environment variables."""
        return cls(
            enabled=os.getenv("WHATSAPP_ENABLED", "false").lower() == "true",
            provider=os.getenv("WHATSAPP_PROVIDER", "twilio"),
            api_key=os.getenv("WHATSAPP_API_KEY", ""),
            api_url=os.getenv("WHATSAPP_API_URL", ""),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_whatsapp_number=os.getenv("TWILIO_WHATSAPP_NUMBER", ""),
            from_number=os.getenv("WHATSAPP_FROM_NUMBER", ""),
        )


@dataclass
class WhatsAppMessage:
    """WhatsApp message data."""
    
    to_number: str
    message_type: WhatsAppMessageType = WhatsAppMessageType.TEXT
    content: str = ""
    media_url: Optional[str] = None
    template_name: Optional[str] = None
    template_params: List[str] = field(default_factory=list)
    
    # Interactive message options
    buttons: List[Dict[str, str]] = field(default_factory=list)
    
    # Metadata
    priority: str = "normal"
    category: str = "utility"  # utility, marketing, authentication


@dataclass
class WhatsAppResult:
    """Result of WhatsApp send operation."""
    
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    status: str = "sent"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "message_id": self.message_id,
            "error": self.error,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        }


class WhatsAppService:
    """
    WhatsApp service for RefurbAdmin AI.
    
    Features:
    - Send text messages
    - Send media (images, documents)
    - Template messages
    - Interactive messages with buttons
    - South African phone number formatting
    - Rate limiting
    """
    
    def __init__(self, config: Optional[WhatsAppConfig] = None):
        self.config = config or WhatsAppConfig()
        self._sent_count = 0
        self._last_send_time: Optional[datetime] = None
        
        logger.info(f"WhatsApp service initialized (enabled: {self.config.enabled})")
    
    def format_sa_number(self, phone_number: str) -> str:
        """
        Format South African phone number for WhatsApp.
        
        Args:
            phone_number: Raw phone number
            
        Returns:
            Formatted number (e.g., +27821234567)
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone_number)
        
        # Handle different formats
        if digits.startswith('27'):
            # Already international format without +
            return f"+{digits}"
        elif digits.startswith('0'):
            # Local format (082...)
            return f"+27{digits[1:]}"
        elif len(digits) == 9:
            # Just the number (821234567)
            return f"+27{digits}"
        elif digits.startswith('+'):
            # Already formatted
            return digits
        else:
            # Assume it's already in correct format
            return f"+{digits}"
    
    def validate_sa_number(self, phone_number: str) -> bool:
        """
        Validate South African phone number.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid SA number
        """
        formatted = self.format_sa_number(phone_number)
        
        # Check format: +27 followed by 9 digits
        pattern = r'^\+27[0-9]{9}$'
        
        if not re.match(pattern, formatted):
            return False
        
        # Check valid mobile prefixes
        mobile_prefixes = ['60', '61', '62', '63', '64', '65', '70', '71', '72', 
                          '73', '74', '75', '76', '77', '78', '79', '80', '81', 
                          '82', '83', '84', '85', '86', '87', '88', '89']
        
        # Extract prefix after +27
        prefix = formatted[3:5]
        
        # Allow landline prefixes too (01x, 02x, 03x, 04x, 05x)
        landline_prefixes = ['10', '11', '12', '13', '14', '15', '16', '17', '18',
                            '21', '22', '23', '24', '25', '26', '27', '28', '29',
                            '31', '32', '33', '34', '35', '36', '39',
                            '40', '41', '42', '43', '44', '45', '46', '47', '48', '49',
                            '51', '53', '54', '56', '57', '58']
        
        return prefix in mobile_prefixes or prefix in landline_prefixes
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        if self._last_send_time:
            elapsed = (datetime.utcnow() - self._last_send_time).total_seconds()
            if elapsed < 60 and self._sent_count >= self.config.rate_limit_per_minute:
                return False
        return True
    
    def send_message(self, message: WhatsAppMessage) -> WhatsAppResult:
        """
        Send a WhatsApp message.
        
        Args:
            message: WhatsAppMessage to send
            
        Returns:
            WhatsAppResult with send status
        """
        if not self.config.enabled:
            return WhatsAppResult(
                success=False,
                error="WhatsApp service is disabled",
            )
        
        # Validate phone number
        formatted_number = self.format_sa_number(message.to_number)
        
        if not self.validate_sa_number(message.to_number):
            logger.warning(f"Invalid WhatsApp number: {message.to_number}")
            return WhatsAppResult(
                success=False,
                error=f"Invalid phone number: {message.to_number}",
            )
        
        # Check rate limit
        if not self._check_rate_limit():
            return WhatsAppResult(
                success=False,
                error="Rate limit exceeded",
            )
        
        try:
            # Send based on provider
            if self.config.provider == "twilio":
                result = self._send_via_twilio(message, formatted_number)
            elif self.config.provider == "360dialog":
                result = self._send_via_360dialog(message, formatted_number)
            elif self.config.provider == "meta":
                result = self._send_via_meta(message, formatted_number)
            else:
                result = WhatsAppResult(
                    success=False,
                    error=f"Unknown provider: {self.config.provider}",
                )
            
            # Update counters
            if result.success:
                self._sent_count += 1
                self._last_send_time = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return WhatsAppResult(
                success=False,
                error=str(e),
            )
    
    def _send_via_twilio(self, message: WhatsAppMessage, to_number: str) -> WhatsAppResult:
        """Send message via Twilio."""
        try:
            from twilio.rest import Client
            
            client = Client(
                self.config.twilio_account_sid,
                self.config.twilio_auth_token
            )
            
            # Build message content
            if message.message_type == WhatsAppMessageType.TEXT:
                body = message.content
            elif message.message_type == WhatsAppMessageType.TEMPLATE:
                # Template messages via Twilio
                body = message.content  # Template content
            else:
                body = message.content
            
            whatsapp_from = f"whatsapp:{self.config.twilio_whatsapp_number}"
            whatsapp_to = f"whatsapp:{to_number}"
            
            twilio_message = client.messages.create(
                body=body,
                from_=whatsapp_from,
                to=whatsapp_to,
            )
            
            return WhatsAppResult(
                success=True,
                message_id=twilio_message.sid,
                status=twilio_message.status,
            )
            
        except ImportError:
            return WhatsAppResult(
                success=False,
                error="Twilio library not installed",
            )
        except Exception as e:
            return WhatsAppResult(
                success=False,
                error=str(e),
            )
    
    def _send_via_360dialog(self, message: WhatsAppMessage, to_number: str) -> WhatsAppResult:
        """Send message via 360dialog."""
        try:
            import requests
            
            url = f"{self.config.api_url}/v1/messages"
            
            headers = {
                "D360-API-KEY": self.config.api_key,
                "Content-Type": "application/json",
            }
            
            payload = {
                "to": to_number.replace('+', ''),
                "type": message.message_type.value,
            }
            
            if message.message_type == WhatsAppMessageType.TEXT:
                payload["text"] = {"body": message.content}
            elif message.message_type == WhatsAppMessageType.TEMPLATE:
                payload["template"] = {
                    "name": message.template_name,
                    "language": {"code": self.config.default_template_language},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": param}
                                for param in message.template_params
                            ]
                        }
                    ]
                }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return WhatsAppResult(
                    success=True,
                    message_id=data.get("messages", [{}])[0].get("id"),
                )
            else:
                return WhatsAppResult(
                    success=False,
                    error=f"API error: {response.status_code} - {response.text}",
                )
                
        except Exception as e:
            return WhatsAppResult(
                success=False,
                error=str(e),
            )
    
    def _send_via_meta(self, message: WhatsAppMessage, to_number: str) -> WhatsAppResult:
        """Send message via Meta WhatsApp Business API."""
        try:
            import requests
            
            url = f"{self.config.api_url}/{self.config.phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number.replace('+', ''),
                "type": message.message_type.value,
            }
            
            if message.message_type == WhatsAppMessageType.TEXT:
                payload["text"] = {"body": message.content}
            elif message.message_type == WhatsAppMessageType.TEMPLATE:
                payload["template"] = {
                    "name": message.template_name,
                    "language": {"code": self.config.default_template_language},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": param}
                                for param in message.template_params
                            ]
                        }
                    ]
                }
            elif message.message_type == WhatsAppMessageType.INTERACTIVE:
                payload["interactive"] = {
                    "type": "button",
                    "body": {"text": message.content},
                    "action": {
                        "buttons": message.buttons
                    }
                }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return WhatsAppResult(
                    success=True,
                    message_id=data.get("messages", [{}])[0].get("id"),
                )
            else:
                return WhatsAppResult(
                    success=False,
                    error=f"API error: {response.status_code} - {response.text}",
                )
                
        except Exception as e:
            return WhatsAppResult(
                success=False,
                error=str(e),
            )
    
    # =========================================================================
    # Convenience Methods for Common Message Types
    # =========================================================================
    
    def send_quick_quote(
        self,
        to_number: str,
        customer_name: str,
        quote_total: float,
        quote_valid_until: str,
    ) -> WhatsAppResult:
        """
        Send a quick quote via WhatsApp.
        
        Args:
            to_number: Customer phone number
            customer_name: Customer name
            quote_total: Total quote amount in ZAR
            quote_valid_until: Quote validity date
        """
        message = WhatsAppMessage(
            to_number=to_number,
            message_type=WhatsAppMessageType.TEXT,
            content=f"""
Hi {customer_name}! 👋

Here's your quick quote from RefurbAdmin AI:

💰 Total: R{quote_total:.2f}
📅 Valid until: {quote_valid_until}

To accept this quote, reply YES or visit:
refurbadmin.co.za/quotes

Questions? Reply to this message!

Thank you for choosing RefurbAdmin AI 🇿🇦
""",
        )
        
        return self.send_message(message)
    
    def send_repair_status(
        self,
        to_number: str,
        customer_name: str,
        repair_number: str,
        status: str,
        device_name: str,
    ) -> WhatsAppResult:
        """
        Send repair status update via WhatsApp.
        
        Args:
            to_number: Customer phone number
            customer_name: Customer name
            repair_number: Repair reference
            status: Repair status
            device_name: Device name
        """
        status_emoji = {
            "received": "📦",
            "diagnosing": "🔍",
            "waiting_parts": "⏳",
            "in_progress": "🔧",
            "completed": "✅",
            "ready_for_collection": "🎉",
            "collected": "👋",
        }
        
        message = WhatsAppMessage(
            to_number=to_number,
            message_type=WhatsAppMessageType.TEXT,
            content=f"""
{status_emoji.get(status, "📱")} Repair Update

Hi {customer_name}!

Your {device_name} repair status:
📋 Ref: {repair_number}
📊 Status: {status.replace('_', ' ').title()}

Track your repair:
refurbadmin.co.za/repairs/{repair_number}

RefurbAdmin AI 🇿🇦
""",
        )
        
        return self.send_message(message)
    
    def send_quote_followup(
        self,
        to_number: str,
        customer_name: str,
        quote_number: str,
        quote_amount: float,
        days_remaining: int,
    ) -> WhatsAppResult:
        """
        Send quote follow-up message.
        
        Args:
            to_number: Customer phone number
            customer_name: Customer name
            quote_number: Quote reference
            quote_amount: Quote amount
            days_remaining: Days until quote expires
        """
        message = WhatsAppMessage(
            to_number=to_number,
            message_type=WhatsAppMessageType.INTERACTIVE,
            content=f"""
Hi {customer_name}! 👋

Just following up on your quote #{quote_number}.

💰 Amount: R{quote_amount:.2f}
⏰ Expires in: {days_remaining} days

Would you like to proceed?
""",
            buttons=[
                {"type": "reply", "reply": {"id": "accept_quote", "title": "✅ Accept"}},
                {"type": "reply", "reply": {"id": "extend_quote", "title": "📅 Extend"}},
                {"type": "reply", "reply": {"id": "speak_agent", "title": "💬 Agent"}},
            ],
        )
        
        return self.send_message(message)
    
    def send_payment_reminder(
        self,
        to_number: str,
        customer_name: str,
        invoice_number: str,
        amount_due: float,
        due_date: str,
    ) -> WhatsAppResult:
        """
        Send payment reminder via WhatsApp.
        
        Args:
            to_number: Customer phone number
            customer_name: Customer name
            invoice_number: Invoice reference
            amount_due: Amount due in ZAR
            due_date: Payment due date
        """
        message = WhatsAppMessage(
            to_number=to_number,
            message_type=WhatsAppMessageType.TEXT,
            content=f"""
💳 Payment Reminder

Hi {customer_name},

This is a friendly reminder about your outstanding payment:

📋 Invoice: {invoice_number}
💰 Amount: R{amount_due:.2f}
📅 Due: {due_date}

Pay securely at:
refurbadmin.co.za/pay/{invoice_number}

Questions? Reply to this message!

RefurbAdmin AI 🇿🇦
""",
        )
        
        return self.send_message(message)
    
    def send_collection_ready(
        self,
        to_number: str,
        customer_name: str,
        repair_number: str,
        device_name: str,
        store_address: str,
        store_hours: str,
    ) -> WhatsAppResult:
        """
        Send collection ready notification.
        
        Args:
            to_number: Customer phone number
            customer_name: Customer name
            repair_number: Repair reference
            device_name: Device name
            store_address: Store address
            store_hours: Store hours
        """
        message = WhatsAppMessage(
            to_number=to_number,
            message_type=WhatsAppMessageType.TEXT,
            content=f"""
🎉 Ready for Collection!

Hi {customer_name},

Great news! Your {device_name} is ready for collection.

📋 Ref: {repair_number}
📍 Address: {store_address}
🕐 Hours: {store_hours}

Please bring:
- This message
- Your ID document
- Proof of purchase

See you soon! 👋

RefurbAdmin AI 🇿🇦
""",
        )
        
        return self.send_message(message)


# =============================================================================
# Singleton
# =============================================================================

_whatsapp_service_instance: Optional[WhatsAppService] = None


def get_whatsapp_service(config: Optional[WhatsAppConfig] = None) -> WhatsAppService:
    """Get or create the WhatsApp service singleton."""
    global _whatsapp_service_instance
    
    if _whatsapp_service_instance is None:
        _whatsapp_service_instance = WhatsAppService(config=config)
    
    return _whatsapp_service_instance
