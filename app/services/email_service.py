"""
Email Service for RefurbAdmin AI.

Provides email notification capabilities:
- Repair status updates
- Quote follow-ups
- Low stock alerts
- SMTP configuration for South African providers

Supports:
- Gmail/Office365
- Hetzner (SA hosting)
- Afrihost (SA hosting)
- Custom SMTP servers
"""

import os
import logging
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from pathlib import Path
from datetime import datetime
import smtplib
from jinja2 import Template

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration."""
    
    # SMTP settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    use_tls: bool = True
    use_ssl: bool = False
    
    # Sender settings
    from_email: str = "noreply@refurbadmin.co.za"
    from_name: str = "RefurbAdmin AI"
    
    # Reply-to
    reply_to: Optional[str] = None
    
    # Timezone (South African)
    timezone: str = "Africa/Johannesburg"
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    @classmethod
    def from_env(cls) -> "EmailConfig":
        """Create config from environment variables."""
        return cls(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            from_email=os.getenv("SMTP_FROM_EMAIL", "noreply@refurbadmin.co.za"),
            from_name=os.getenv("SMTP_FROM_NAME", "RefurbAdmin AI"),
            reply_to=os.getenv("SMTP_REPLY_TO"),
        )
    
    @classmethod
    def for_provider(cls, provider: str) -> "EmailConfig":
        """Create config for specific email provider."""
        providers = {
            "gmail": {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
            },
            "office365": {
                "smtp_host": "smtp.office365.com",
                "smtp_port": 587,
                "use_tls": True,
            },
            "hetzner": {  # South African hosting
                "smtp_host": "smtp.hetzner.co.za",
                "smtp_port": 587,
                "use_tls": True,
            },
            "afrihost": {  # South African hosting
                "smtp_host": "smtp.afrihost.co.za",
                "smtp_port": 587,
                "use_tls": True,
            },
            "telkom": {  # South African ISP
                "smtp_host": "smtp.telkom.co.za",
                "smtp_port": 587,
                "use_tls": False,
            },
        }
        
        config = providers.get(provider.lower())
        if config:
            return cls(**config)
        
        raise ValueError(f"Unknown email provider: {provider}")


@dataclass
class EmailMessage:
    """Email message data."""
    
    subject: str
    body_text: str
    body_html: Optional[str] = None
    to_emails: List[str] = field(default_factory=list)
    cc_emails: List[str] = field(default_factory=list)
    bcc_emails: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    attachments: List[Union[str, Path]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Template context
    template_name: Optional[str] = None
    template_context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    priority: str = "normal"  # high, normal, low
    category: str = "transactional"  # transactional, marketing, notification
    
    def add_attachment(self, file_path: Union[str, Path], filename: Optional[str] = None):
        """Add attachment to email."""
        self.attachments.append(file_path)


@dataclass
class EmailResult:
    """Result of email send operation."""
    
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    recipients_accepted: List[str] = field(default_factory=list)
    recipients_rejected: List[str] = field(default_factory=list)
    send_time: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "message_id": self.message_id,
            "error": self.error,
            "recipients_accepted": self.recipients_accepted,
            "recipients_rejected": self.recipients_rejected,
            "send_time": self.send_time.isoformat(),
        }


class EmailService:
    """
    Email service for RefurbAdmin AI.
    
    Features:
    - SMTP email sending
    - HTML and text emails
    - Attachments
    - Email templates
    - Rate limiting
    - Retry logic
    - South African provider support
    """
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
        self._sent_count = 0
        self._last_send_time: Optional[datetime] = None
        
        # Load email templates
        self._templates: Dict[str, Template] = {}
        self._load_templates()
        
        logger.info(f"Email service initialized with SMTP host: {self.config.smtp_host}")
    
    def _load_templates(self):
        """Load email templates."""
        templates_dir = Path(__file__).parent.parent / "templates" / "emails"
        
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.html"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        self._templates[template_file.stem] = Template(f.read())
                except Exception as e:
                    logger.warning(f"Failed to load template {template_file}: {e}")
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        if self._last_send_time:
            elapsed = (datetime.utcnow() - self._last_send_time).total_seconds()
            if elapsed < 60 and self._sent_count >= self.config.rate_limit_per_minute:
                return False
        return True
    
    def _wait_for_rate_limit(self):
        """Wait if rate limit is exceeded."""
        import time
        
        while not self._check_rate_limit():
            time.sleep(1)
    
    def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send an email message.
        
        Args:
            message: EmailMessage to send
            
        Returns:
            EmailResult with send status
        """
        # Check rate limit
        self._wait_for_rate_limit()
        
        try:
            # Render template if provided
            if message.template_name and message.template_name in self._templates:
                template = self._templates[message.template_name]
                message.body_html = template.render(**message.template_context)
                message.body_text = template.render(**message.template_context)
            
            # Create message
            msg = self._create_message(message)
            
            # Send with retry
            result = self._send_with_retry(msg, message)
            
            # Update counters
            if result.success:
                self._sent_count += 1
                self._last_send_time = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return EmailResult(
                success=False,
                error=str(e),
            )
    
    def _create_message(self, email: EmailMessage) -> MIMEMultipart:
        """Create MIME message."""
        msg = MIMEMultipart('alternative')
        
        # Headers
        msg['Subject'] = email.subject
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = ', '.join(email.to_emails)
        
        if email.cc_emails:
            msg['Cc'] = ', '.join(email.cc_emails)
        
        if email.reply_to:
            msg['Reply-To'] = email.reply_to
        elif self.config.reply_to:
            msg['Reply-To'] = self.config.reply_to
        
        # Priority header
        priority_map = {
            'high': '1 (Highest)',
            'normal': '3 (Normal)',
            'low': '5 (Lowest)',
        }
        msg['X-Priority'] = priority_map.get(email.priority, '3 (Normal)')
        
        # Custom headers
        for key, value in email.headers.items():
            msg[key] = value
        
        # Body
        if email.body_text:
            msg.attach(MIMEText(email.body_text, 'plain', 'utf-8'))
        
        if email.body_html:
            msg.attach(MIMEText(email.body_html, 'html', 'utf-8'))
        
        # Attachments
        for attachment in email.attachments:
            self._add_attachment(msg, attachment)
        
        return msg
    
    def _add_attachment(self, msg: MIMEMultipart, file_path: Union[str, Path]):
        """Add attachment to message."""
        path = Path(file_path)
        
        if not path.exists():
            logger.warning(f"Attachment not found: {file_path}")
            return
        
        try:
            with open(path, 'rb') as f:
                # Determine content type
                if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                    part = MIMEImage(f.read())
                else:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{path.name}"'
                )
                msg.attach(part)
                
        except Exception as e:
            logger.warning(f"Failed to add attachment {file_path}: {e}")
    
    def _send_with_retry(self, msg: MIMEMultipart, email: EmailMessage) -> EmailResult:
        """Send email with retry logic."""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return self._send_smtp(msg, email)
            except Exception as e:
                last_error = e
                logger.warning(f"Email send attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.max_retries - 1:
                    import time
                    time.sleep(self.config.retry_delay_seconds * (attempt + 1))
        
        return EmailResult(
            success=False,
            error=f"Failed after {self.config.max_retries} attempts: {last_error}",
        )
    
    def _send_smtp(self, msg: MIMEMultipart, email: EmailMessage) -> EmailResult:
        """Send email via SMTP."""
        # Collect all recipients
        all_recipients = email.to_emails + email.cc_emails + email.bcc_emails
        
        if self.config.use_ssl:
            server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port)
        else:
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
        
        try:
            # Enable TLS if configured
            if self.config.use_tls and not self.config.use_ssl:
                server.starttls()
            
            # Login if credentials provided
            if self.config.smtp_user and self.config.smtp_password:
                server.login(self.config.smtp_user, self.config.smtp_password)
            
            # Send email
            server.send_message(msg, from_addr=self.config.from_email, to_addrs=all_recipients)
            
            # Get message ID
            message_id = msg.get('Message-ID', 'unknown')
            
            return EmailResult(
                success=True,
                message_id=message_id,
                recipients_accepted=all_recipients,
            )
            
        finally:
            server.quit()
    
    # =========================================================================
    # Convenience Methods for Common Email Types
    # =========================================================================
    
    def send_quote_email(
        self,
        to_email: str,
        quote_number: str,
        customer_name: str,
        total_amount: float,
        items: List[Dict[str, Any]],
        valid_until: datetime,
    ) -> EmailResult:
        """
        Send quote email to customer.
        
        Args:
            to_email: Customer email
            quote_number: Quote reference number
            customer_name: Customer name
            total_amount: Total quote amount in ZAR
            items: List of quote items
            valid_until: Quote validity date
        """
        subject = f"Your Quote #{quote_number} from RefurbAdmin AI"
        
        # Text body
        text_body = f"""
Dear {customer_name},

Thank you for your interest in RefurbAdmin AI.

Please find your quote details below:

Quote Number: {quote_number}
Valid Until: {valid_until.strftime('%d %B %Y')}

Items:
"""
        for item in items:
            text_body += f"- {item.get('name', 'Item')}: R{item.get('price', 0):.2f} x {item.get('quantity', 1)}\n"
        
        text_body += f"""
Total: R{total_amount:.2f}

To accept this quote, please reply to this email or contact us at 0800 REFURB.

Kind regards,
RefurbAdmin AI Team
www.refurbadmin.co.za
"""
        
        # HTML body
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2 style="color: #2c5282;">Your Quote #{quote_number}</h2>
    
    <p>Dear {customer_name},</p>
    
    <p>Thank you for your interest in RefurbAdmin AI.</p>
    
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr style="background-color: #2c5282; color: white;">
            <th style="padding: 10px; text-align: left;">Item</th>
            <th style="padding: 10px;">Quantity</th>
            <th style="padding: 10px;">Price</th>
            <th style="padding: 10px;">Total</th>
        </tr>
"""
        for item in items:
            name = item.get('name', 'Item')
            qty = item.get('quantity', 1)
            price = item.get('price', 0)
            total = qty * price
            html_body += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 10px;">{name}</td>
            <td style="padding: 10px; text-align: center;">{qty}</td>
            <td style="padding: 10px; text-align: right;">R{price:.2f}</td>
            <td style="padding: 10px; text-align: right;">R{total:.2f}</td>
        </tr>
"""
        
        html_body += f"""
        <tr style="background-color: #f7fafc; font-weight: bold;">
            <td colspan="3" style="padding: 10px; text-align: right;">Total:</td>
            <td style="padding: 10px; text-align: right; color: #2c5282;">R{total_amount:.2f}</td>
        </tr>
    </table>
    
    <p><strong>Valid Until:</strong> {valid_until.strftime('%d %B %Y')}</p>
    
    <p style="margin-top: 30px;">
        <a href="https://refurbadmin.co.za/quotes/{quote_number}/accept" 
           style="background-color: #48bb78; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            Accept Quote
        </a>
    </p>
    
    <p style="margin-top: 30px; color: #718096; font-size: 14px;">
        Kind regards,<br>
        RefurbAdmin AI Team<br>
        📞 0800 REFURB<br>
        🌐 www.refurbadmin.co.za
    </p>
</body>
</html>
"""
        
        message = EmailMessage(
            subject=subject,
            body_text=text_body,
            body_html=html_body,
            to_emails=[to_email],
            category="transactional",
        )
        
        return self.send_email(message)
    
    def send_repair_status_email(
        self,
        to_email: str,
        customer_name: str,
        repair_number: str,
        status: str,
        device_name: str,
        notes: Optional[str] = None,
    ) -> EmailResult:
        """
        Send repair status update email.
        
        Args:
            to_email: Customer email
            customer_name: Customer name
            repair_number: Repair reference number
            status: Repair status
            device_name: Device being repaired
            notes: Additional notes
        """
        status_colors = {
            "received": "#4299e1",
            "diagnosing": "#ed8936",
            "waiting_parts": "#ecc94b",
            "in_progress": "#4299e1",
            "completed": "#48bb78",
            "ready_for_collection": "#48bb78",
            "collected": "#718096",
        }
        
        status_messages = {
            "received": "We have received your device and will begin diagnosis shortly.",
            "diagnosing": "Your device is being diagnosed by our technicians.",
            "waiting_parts": "We are waiting for parts to arrive for your repair.",
            "in_progress": "Your device is being repaired.",
            "completed": "Your device has been repaired and is ready for collection.",
            "ready_for_collection": "Your device is ready for collection at our store.",
            "collected": "Your device has been collected. Thank you for choosing RefurbAdmin AI!",
        }
        
        subject = f"Repair Update #{repair_number} - {status.replace('_', ' ').title()}"
        
        text_body = f"""
Dear {customer_name},

Your {device_name} repair status has been updated.

Repair Number: {repair_number}
Current Status: {status.replace('_', ' ').title()}

{status_messages.get(status, '')}

"""
        if notes:
            text_body += f"Notes: {notes}\n"
        
        text_body += """
You can check your repair status anytime at www.refurbadmin.co.za/repairs

Kind regards,
RefurbAdmin AI Team
"""
        
        color = status_colors.get(status, "#718096")
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2 style="color: {color};">Repair Status Update</h2>
    
    <p>Dear {customer_name},</p>
    
    <div style="background-color: #f7fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p><strong>Device:</strong> {device_name}</p>
        <p><strong>Repair Number:</strong> {repair_number}</p>
        <p><strong>Status:</strong> 
            <span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 4px;">
                {status.replace('_', ' ').title()}
            </span>
        </p>
    </div>
    
    <p>{status_messages.get(status, '')}</p>
    
    {f'<p style="color: #718096;"><em>{notes}</em></p>' if notes else ''}
    
    <p style="margin-top: 30px;">
        <a href="https://refurbadmin.co.za/repairs/{repair_number}" 
           style="background-color: #4299e1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            View Repair Status
        </a>
    </p>
    
    <p style="margin-top: 30px; color: #718096; font-size: 14px;">
        Kind regards,<br>
        RefurbAdmin AI Team<br>
        📞 0800 REFURB
    </p>
</body>
</html>
"""
        
        message = EmailMessage(
            subject=subject,
            body_text=text_body,
            body_html=html_body,
            to_emails=[to_email],
            category="notification",
        )
        
        return self.send_email(message)
    
    def send_low_stock_alert(
        self,
        to_emails: List[str],
        product_name: str,
        current_stock: int,
        minimum_stock: int,
        supplier_name: Optional[str] = None,
    ) -> EmailResult:
        """
        Send low stock alert to management.
        
        Args:
            to_emails: Management emails
            product_name: Product name
            current_stock: Current stock level
            minimum_stock: Minimum stock threshold
            supplier_name: Supplier name
        """
        subject = f"⚠️ Low Stock Alert: {product_name}"
        
        text_body = f"""
LOW STOCK ALERT

Product: {product_name}
Current Stock: {current_stock}
Minimum Threshold: {minimum_stock}

This product has fallen below the minimum stock level.

"""
        if supplier_name:
            text_body += f"Supplier: {supplier_name}\n"
        
        text_body += """
Please consider reordering soon.

RefurbAdmin AI Inventory System
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <div style="background-color: #fed7d7; border-left: 4px solid #e53e3e; padding: 16px; margin: 20px 0;">
        <h3 style="color: #c53030; margin: 0;">⚠️ Low Stock Alert</h3>
    </div>
    
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Product:</td>
            <td style="padding: 8px;">{product_name}</td>
        </tr>
        <tr style="background-color: #fff5f5;">
            <td style="padding: 8px; font-weight: bold;">Current Stock:</td>
            <td style="padding: 8px; color: #e53e3e; font-weight: bold;">{current_stock}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Minimum Threshold:</td>
            <td style="padding: 8px;">{minimum_stock}</td>
        </tr>
        {f'<tr><td style="padding: 8px; font-weight: bold;">Supplier:</td><td style="padding: 8px;">{supplier_name}</td></tr>' if supplier_name else ''}
    </table>
    
    <p style="margin-top: 20px;">
        <a href="https://refurbadmin.co.za/inventory" 
           style="background-color: #4299e1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            View Inventory
        </a>
    </p>
    
    <p style="margin-top: 30px; color: #718096; font-size: 14px;">
        RefurbAdmin AI Inventory System
    </p>
</body>
</html>
"""
        
        message = EmailMessage(
            subject=subject,
            body_text=text_body,
            body_html=html_body,
            to_emails=to_emails,
            priority="high",
            category="notification",
        )
        
        return self.send_email(message)
    
    def send_welcome_email(
        self,
        to_email: str,
        customer_name: str,
        login_url: str = "https://refurbadmin.co.za/login",
    ) -> EmailResult:
        """
        Send welcome email to new customer.
        
        Args:
            to_email: Customer email
            customer_name: Customer name
            login_url: Login URL
        """
        subject = "Welcome to RefurbAdmin AI!"
        
        text_body = f"""
Dear {customer_name},

Welcome to RefurbAdmin AI!

We're excited to have you on board. You can now:
- Get instant quotes for refurbished electronics
- Track your repair status online
- Browse our latest inventory
- Access exclusive deals

Get started by logging in: {login_url}

Kind regards,
RefurbAdmin AI Team
www.refurbadmin.co.za
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h1 style="color: #2c5282;">Welcome to RefurbAdmin AI! 🎉</h1>
    
    <p>Dear {customer_name},</p>
    
    <p>We're excited to have you on board!</p>
    
    <div style="background-color: #f7fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3 style="color: #2c5282; margin-top: 0;">You can now:</h3>
        <ul style="line-height: 2;">
            <li>✅ Get instant quotes for refurbished electronics</li>
            <li>✅ Track your repair status online</li>
            <li>✅ Browse our latest inventory</li>
            <li>✅ Access exclusive deals</li>
        </ul>
    </div>
    
    <p style="margin-top: 30px;">
        <a href="{login_url}" 
           style="background-color: #48bb78; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            Get Started
        </a>
    </p>
    
    <p style="margin-top: 30px; color: #718096; font-size: 14px;">
        Kind regards,<br>
        RefurbAdmin AI Team<br>
        📞 0800 REFURB<br>
        🌐 www.refurbadmin.co.za
    </p>
</body>
</html>
"""
        
        message = EmailMessage(
            subject=subject,
            body_text=text_body,
            body_html=html_body,
            to_emails=[to_email],
            category="transactional",
        )
        
        return self.send_email(message)


# =============================================================================
# Singleton
# =============================================================================

_email_service_instance: Optional[EmailService] = None


def get_email_service(config: Optional[EmailConfig] = None) -> EmailService:
    """Get or create the email service singleton."""
    global _email_service_instance
    
    if _email_service_instance is None:
        _email_service_instance = EmailService(config=config)
    
    return _email_service_instance
