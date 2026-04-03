"""
Report Generator for RefurbAdmin AI.

Provides PDF report generation:
- Inventory reports
- Sales reports
- Margin analysis
- Email attachment ready

Uses ReportLab for PDF generation with South African formatting.
"""

import os
import io
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Report configuration."""
    
    # Company info
    company_name: str = "RefurbAdmin AI"
    company_address: str = "123 Main Street, Johannesburg, 2001"
    company_phone: str = "0800 REFURB"
    company_email: str = "info@refurbadmin.co.za"
    company_website: str = "www.refurbadmin.co.za"
    
    # Report settings
    page_size: tuple = A4
    currency_symbol: str = "R"
    date_format: str = "%d %B %Y"
    timezone: str = "Africa/Johannesburg"
    
    # Branding
    logo_path: Optional[str] = None
    primary_color: str = "#2c5282"
    secondary_color: str = "#48bb78"
    
    @classmethod
    def from_env(cls) -> "ReportConfig":
        """Create config from environment variables."""
        return cls(
            company_name=os.getenv("COMPANY_NAME", "RefurbAdmin AI"),
            company_address=os.getenv("COMPANY_ADDRESS", ""),
            company_phone=os.getenv("COMPANY_PHONE", "0800 REFURB"),
            company_email=os.getenv("COMPANY_EMAIL", "info@refurbadmin.co.za"),
            company_website=os.getenv("COMPANY_WEBSITE", "www.refurbadmin.co.za"),
            logo_path=os.getenv("REPORT_LOGO_PATH"),
        )


@dataclass
class ReportResult:
    """Result of report generation."""
    
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    pages: int = 0
    error: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "file_path": self.file_path,
            "file_size_kb": round(self.file_size / 1024, 2),
            "pages": self.pages,
            "error": self.error,
            "generated_at": self.generated_at.isoformat(),
        }


class ReportGenerator:
    """
    PDF report generator for RefurbAdmin AI.
    
    Features:
    - Inventory reports
    - Sales reports
    - Margin analysis
    - Custom branding
    - Email attachment ready
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        
        logger.info("Report generator initialized")
    
    def _setup_styles(self):
        """Setup custom styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.config.primary_color,
            spaceAfter=30,
            alignment=TA_CENTER,
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.config.primary_color,
            spaceAfter=12,
        ))
        
        # Normal style
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
        ))
        
        # Right aligned for numbers
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT,
        ))
        
        # Center aligned
        self.styles.add(ParagraphStyle(
            name='CenterAlign',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
        ))
    
    def generate_inventory_report(
        self,
        inventory_items: List[Dict[str, Any]],
        output_path: Optional[str] = None,
        include_summary: bool = True,
    ) -> ReportResult:
        """
        Generate inventory report.
        
        Args:
            inventory_items: List of inventory items
            output_path: Output file path
            include_summary: Include summary section
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = output_path or f"inventory_report_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=self.config.page_size,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header())
        elements.append(Spacer(1, 0.5*inch))
        
        # Title
        elements.append(Paragraph("Inventory Report", self.styles['CustomTitle']))
        elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime(self.config.date_format)}", self.styles['CenterAlign']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Summary
        if include_summary:
            elements.extend(self._create_inventory_summary(inventory_items))
            elements.append(Spacer(1, 0.3*inch))
        
        # Inventory table
        elements.extend(self._create_inventory_table(inventory_items))
        
        # Build PDF
        try:
            doc.build(elements)
            
            return ReportResult(
                success=True,
                file_path=filename,
                file_size=Path(filename).stat().st_size,
                pages=doc.page,
            )
        except Exception as e:
            return ReportResult(
                success=False,
                error=str(e),
            )
    
    def generate_sales_report(
        self,
        sales_data: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        output_path: Optional[str] = None,
    ) -> ReportResult:
        """
        Generate sales report.
        
        Args:
            sales_data: List of sales records
            start_date: Report start date
            end_date: Report end date
            output_path: Output file path
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = output_path or f"sales_report_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=self.config.page_size,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header())
        elements.append(Spacer(1, 0.5*inch))
        
        # Title
        elements.append(Paragraph("Sales Report", self.styles['CustomTitle']))
        elements.append(Paragraph(
            f"Period: {start_date.strftime(self.config.date_format)} - {end_date.strftime(self.config.date_format)}",
            self.styles['CenterAlign']
        ))
        elements.append(Spacer(1, 0.5*inch))
        
        # Sales summary
        elements.extend(self._create_sales_summary(sales_data))
        elements.append(Spacer(1, 0.3*inch))
        
        # Sales table
        elements.extend(self._create_sales_table(sales_data))
        
        # Build PDF
        try:
            doc.build(elements)
            
            return ReportResult(
                success=True,
                file_path=filename,
                file_size=Path(filename).stat().st_size,
                pages=doc.page,
            )
        except Exception as e:
            return ReportResult(
                success=False,
                error=str(e),
            )
    
    def generate_margin_analysis(
        self,
        products: List[Dict[str, Any]],
        output_path: Optional[str] = None,
    ) -> ReportResult:
        """
        Generate margin analysis report.
        
        Args:
            products: List of products with cost and selling prices
            output_path: Output file path
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = output_path or f"margin_analysis_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=self.config.page_size,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header())
        elements.append(Spacer(1, 0.5*inch))
        
        # Title
        elements.append(Paragraph("Margin Analysis Report", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Margin table
        elements.extend(self._create_margin_table(products))
        
        # Build PDF
        try:
            doc.build(elements)
            
            return ReportResult(
                success=True,
                file_path=filename,
                file_size=Path(filename).stat().st_size,
                pages=doc.page,
            )
        except Exception as e:
            return ReportResult(
                success=False,
                error=str(e),
            )
    
    def _create_header(self) -> list:
        """Create report header with company info."""
        elements = []
        
        # Company info table
        header_data = [
            [
                Paragraph(f"<b>{self.config.company_name}</b>", self.styles['CustomNormal']),
                Paragraph(f"📞 {self.config.company_phone}", self.styles['RightAlign']),
            ],
            [
                Paragraph(self.config.company_address, self.styles['CustomNormal']),
                Paragraph(f"📧 {self.config.company_email}", self.styles['RightAlign']),
            ],
            [
                [""],
                Paragraph(f"🌐 {self.config.company_website}", self.styles['RightAlign']),
            ],
        ]
        
        header_table = Table(header_data, colWidths=[4*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        
        return elements
    
    def _create_inventory_summary(self, items: List[Dict]) -> list:
        """Create inventory summary section."""
        elements = []
        
        total_items = len(items)
        total_value = sum(item.get('selling_price', 0) * item.get('quantity', 0) for item in items)
        total_cost = sum(item.get('cost_price', 0) * item.get('quantity', 0) for item in items)
        low_stock = sum(1 for item in items if item.get('quantity', 0) < 5)
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Items', str(total_items)],
            ['Total Value', f"{self.config.currency_symbol}{total_value:,.2f}"],
            ['Total Cost', f"{self.config.currency_symbol}{total_cost:,.2f}"],
            ['Potential Profit', f"{self.config.currency_symbol}{total_value - total_cost:,.2f}"],
            ['Low Stock Items', str(low_stock)],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.config.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(Paragraph("Summary", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(summary_table)
        
        return elements
    
    def _create_inventory_table(self, items: List[Dict]) -> list:
        """Create inventory data table."""
        elements = []
        
        elements.append(Paragraph("Inventory Details", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Table headers
        data = [['SKU', 'Product', 'Category', 'Qty', 'Cost', 'Price', 'Value']]
        
        for item in items[:100]:  # Limit to 100 items per page
            data.append([
                item.get('sku', 'N/A'),
                item.get('name', 'Unknown')[:25],
                item.get('category', 'N/A'),
                str(item.get('quantity', 0)),
                f"{self.config.currency_symbol}{item.get('cost_price', 0):.2f}",
                f"{self.config.currency_symbol}{item.get('selling_price', 0):.2f}",
                f"{self.config.currency_symbol}{item.get('quantity', 0) * item.get('selling_price', 0):.2f}",
            ])
        
        table = Table(data, colWidths=[1*inch, 2*inch, 1*inch, 0.6*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.config.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _create_sales_summary(self, sales: List[Dict]) -> list:
        """Create sales summary section."""
        elements = []
        
        total_sales = len(sales)
        total_revenue = sum(sale.get('total', 0) for sale in sales)
        avg_order = total_revenue / total_sales if total_sales > 0 else 0
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Orders', str(total_sales)],
            ['Total Revenue', f"{self.config.currency_symbol}{total_revenue:,.2f}"],
            ['Average Order', f"{self.config.currency_symbol}{avg_order:,.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.config.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(Paragraph("Sales Summary", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(summary_table)
        
        return elements
    
    def _create_sales_table(self, sales: List[Dict]) -> list:
        """Create sales data table."""
        elements = []
        
        elements.append(Paragraph("Sales Details", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        data = [['Date', 'Order #', 'Customer', 'Items', 'Total', 'Status']]
        
        for sale in sales[:100]:
            data.append([
                sale.get('date', 'N/A')[:10],
                sale.get('order_number', 'N/A'),
                sale.get('customer', 'Unknown')[:20],
                str(sale.get('items_count', 0)),
                f"{self.config.currency_symbol}{sale.get('total', 0):.2f}",
                sale.get('status', 'N/A'),
            ])
        
        table = Table(data, colWidths=[1.2*inch, 1.2*inch, 2*inch, 0.6*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.config.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _create_margin_table(self, products: List[Dict]) -> list:
        """Create margin analysis table."""
        elements = []
        
        elements.append(Paragraph("Margin Analysis", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        data = [['Product', 'Cost', 'Price', 'Margin', 'Margin %']]
        
        for product in products[:100]:
            cost = product.get('cost_price', 0)
            price = product.get('selling_price', 0)
            margin = price - cost
            margin_pct = (margin / price * 100) if price > 0 else 0
            
            # Color code margin percentage
            if margin_pct < 20:
                margin_color = 'red'
            elif margin_pct < 40:
                margin_color = 'orange'
            else:
                margin_color = 'green'
            
            data.append([
                product.get('name', 'Unknown')[:30],
                f"{self.config.currency_symbol}{cost:.2f}",
                f"{self.config.currency_symbol}{price:.2f}",
                f"{self.config.currency_symbol}{margin:.2f}",
                f"{margin_pct:.1f}%",
            ])
        
        table = Table(data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.config.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        
        return elements
    
    def generate_to_bytes(
        self,
        report_type: str,
        data: Dict[str, Any],
    ) -> Optional[bytes]:
        """
        Generate report and return as bytes (for email attachment).
        
        Args:
            report_type: Type of report
            data: Report data
            
        Returns:
            PDF bytes or None
        """
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = f.name
        
        try:
            if report_type == "inventory":
                result = self.generate_inventory_report(
                    data.get('items', []),
                    output_path=temp_path,
                )
            elif report_type == "sales":
                result = self.generate_sales_report(
                    data.get('sales', []),
                    start_date=data.get('start_date', datetime.utcnow() - timedelta(days=30)),
                    end_date=data.get('end_date', datetime.utcnow()),
                    output_path=temp_path,
                )
            elif report_type == "margin":
                result = self.generate_margin_analysis(
                    data.get('products', []),
                    output_path=temp_path,
                )
            else:
                return None
            
            if result.success:
                with open(temp_path, 'rb') as f:
                    return f.read()
            return None
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# =============================================================================
# Singleton
# =============================================================================

_report_generator_instance: Optional[ReportGenerator] = None


def get_report_generator(config: Optional[ReportConfig] = None) -> ReportGenerator:
    """Get or create the report generator singleton."""
    global _report_generator_instance
    
    if _report_generator_instance is None:
        _report_generator_instance = ReportGenerator(config=config)
    
    return _report_generator_instance
