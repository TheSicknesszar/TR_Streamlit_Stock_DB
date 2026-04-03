# RefurbAdmin AI

**Inventory & Pricing Automation Platform for IT Refurbishment**

A comprehensive FastAPI-based platform for managing IT refurbishment inventory with dynamic pricing based on South African market conditions.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-proprietary-red)

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Database Models](#-database-models)
- [Pricing Engine](#-pricing-engine)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [South African Context](#-south-african-context)

---

## ✨ Features

### Core Features

- **Dynamic Pricing Engine** - Real-time price calculation based on market data and inventory velocity
- **Inventory Management** - Full CRUD operations for device tracking
- **Serial Number Lookup** - Instant pricing via `/api/v1/price-check` endpoint
- **POPIA Compliance** - Encrypted customer data storage
- **API Authentication** - Secure API key-based authentication

### Pricing Logic

| Condition | Adjustment |
|-----------|------------|
| Slow-moving (>30 days, >5 units) | -10% discount |
| High-demand (<3 units) | +5% premium |
| Normal inventory | No adjustment |

### South African Context

- 🇿🇦 **Currency:** ZAR (R)
- 🕐 **Timezone:** SAST (Africa/Johannesburg)
- 📜 **Compliance:** POPIA-compliant data handling
- 💰 **Retail Pricing:** Psychology-based rounding (R6,499 / R6,999)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Windows 10/11 or Windows Server 2019+
- Git (optional, for version control)

### Installation

1. **Clone or download the project** to your desired location:
   ```
   C:\Users\User\Documents\pricing_tool_est\
   ```

2. **Run the application** using the provided batch file:
   ```batch
   run_app.bat
   ```

   This will:
   - Create a virtual environment (`.venv`)
   - Install all dependencies
   - Create the `.env` configuration file
   - Start the FastAPI server

3. **Access the API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### First API Request

```bash
# Test the health endpoint
curl http://localhost:8000/health

# Create a test device (requires API key)
curl -X POST http://localhost:8000/api/v1/inventory \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "serial_number": "TEST123",
    "make": "Dell",
    "model": "Inspiron 3580",
    "processor": "i5-8265U",
    "ram_gb": 8,
    "ssd_gb": 256,
    "condition_grade": "Grade A",
    "status": "Ready",
    "cost_price": 4500.00
  }'

# Get pricing for the device
curl -X POST http://localhost:8000/api/v1/price-check \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"serial_number": "TEST123"}'
```

---

## 📁 Project Structure

```
pricing_tool_est/
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration settings
│   ├── database.py                # Database setup
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # API dependencies (auth)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # API v1 router
│   │       ├── price_check.py     # /api/v1/price-check endpoint
│   │       └── inventory.py       # Inventory CRUD endpoints
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── device.py              # Device inventory model
│   │   ├── market_price.py        # Market price cache model
│   │   ├── quote.py               # Quote history model
│   │   ├── api_key.py             # API key model
│   │   ├── customer.py            # Customer model (POPIA)
│   │   ├── user.py                # User model
│   │   └── price_history.py       # Price history model
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── pricing.py             # Pricing schemas
│   │   ├── device.py              # Device schemas
│   │   ├── market.py              # Market data schemas
│   │   └── common.py              # Common schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── pricing_service.py     # Pricing engine
│   │
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py          # Currency/date formatters
│       └── validators.py          # Input validators
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   └── test_api/
│       └── test_price_check.py    # Price check tests
│
├── data/
│   ├── raw/                       # Original CSV files
│   ├── processed/                 # Processed data
│   ├── cache/                     # Market price cache
│   └── logs/                      # Application logs
│
├── .env                           # Environment configuration
├── .env.example                   # Environment template
├── requirements.txt               # Python dependencies
├── run_app.bat                    # Windows launcher
└── README.md                      # This file
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```ini
# Application
APP_NAME=RefurbAdmin AI
APP_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./data/refurbadmin_dev.db

# Pricing
DEFAULT_WARRANTY_MONTHS=3
MIN_MARGIN_PERCENT=25
MAX_DISCOUNT_PERCENT=15

# Business Settings
CURRENCY_CODE=ZAR
CURRENCY_SYMBOL=R
TIMEZONE=Africa/Johannesburg
```

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite | Database connection URL |
| `API_KEY_EXPIRY_DAYS` | 90 | API key validity period |
| `SLOW_MOVING_DAYS` | 30 | Days before discount applies |
| `QUOTE_VALIDITY_HOURS` | 48 | Quote validity period |

---

## 📡 API Documentation

### Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

### Authentication

All API endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/...
```

### Core Endpoints

#### POST /api/v1/price-check

Get dynamic pricing for a device by serial number.

**Request:**
```json
{
  "serial_number": "1LW10Y2",
  "include_warranty": true,
  "margin_override": null
}
```

**Response:**
```json
{
  "status": "success",
  "device": {
    "serial": "1LW10Y2",
    "model": "Dell Inspiron 3580",
    "specs": {
      "cpu": "i5-8265U",
      "ram": "8GB",
      "ssd": "256GB",
      "condition": "Grade A Refurbished"
    },
    "inventory_status": "ready",
    "days_in_stock": 14
  },
  "pricing": {
    "base_market_price_zar": 6500.00,
    "velocity_adjustment": 0.00,
    "velocity_adjustment_percent": "0%",
    "final_price_zar": 6500.00,
    "currency": "ZAR",
    "warranty_months": 3,
    "margin_percent": 30.00
  },
  "client_snippet": "We have the Dell Inspiron 3580 (Serial: 1LW10Y2) available for R6,500. Includes 3-month warranty and full quality inspection.",
  "quote_valid_until": "2026-04-03T23:59:59Z"
}
```

#### Inventory Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/inventory` | Create device |
| GET | `/api/v1/inventory` | List devices |
| GET | `/api/v1/inventory/{id}` | Get device |
| PUT | `/api/v1/inventory/{id}` | Update device |
| DELETE | `/api/v1/inventory/{id}` | Delete device |

---

## 🗄️ Database Models

### Device Model

```python
Device:
  - id: UUID
  - serial_number: str (unique)
  - make: str
  - model: str
  - processor: str
  - ram_gb: int
  - ssd_gb: int
  - condition_grade: str (Grade A/B/C, BER, Parts)
  - status: str (Intake, Diagnosis, Waiting Parts, Ready, Sold, BER, Strip)
  - date_received: date
  - cost_price: Decimal
  - sale_price: Decimal
  - created_at: datetime
  - updated_at: datetime
```

### Status Flow

```
Intake → Diagnosis → Waiting Parts → Ready → Sold
                          ↓
                        BER / Strip for Parts
```

---

## 💰 Pricing Engine

### How It Works

1. **Market Data Lookup** - Queries cached market prices for similar devices
2. **Velocity Calculation** - Determines inventory movement speed
3. **Adjustment Application** - Applies discount/premium based on velocity
4. **Retail Rounding** - Rounds to psychology price points

### Pricing Formula

```
final_price = round_to_retail(base_market_price + velocity_adjustment)

where:
  velocity_adjustment = base_market_price × adjustment_percentage
  
adjustment_percentage:
  - Slow-moving (>30 days, >5 units): -10%
  - High-demand (<3 units): +5%
  - Normal: 0%
```

### Retail Price Rounding

| Raw Price | Rounded |
|-----------|---------|
| R6,234 | R5,999 |
| R6,567 | R6,499 |
| R6,789 | R6,999 |
| R7,234 | R6,999 |
| R7,567 | R7,499 |

---

## 🧪 Testing

### Run Tests

```batch
# Activate virtual environment
.venv\Scripts\activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_price_check.py -v
```

### Test Coverage

The project includes tests for:
- ✅ Price check success scenarios
- ✅ Error handling (not found, BER, not ready)
- ✅ Authentication validation
- ✅ Input validation
- ✅ Pricing logic

---

## 🚢 Deployment

### Development (SQLite)

```ini
DATABASE_URL=sqlite+aiosqlite:///./data/refurbadmin_dev.db
APP_ENV=development
DEBUG=True
```

### Production (PostgreSQL)

1. **Install PostgreSQL 15+**

2. **Create database:**
   ```sql
   CREATE DATABASE refurbadmin_ai;
   CREATE USER refurbadmin WITH PASSWORD 'secure-password';
   GRANT ALL PRIVILEGES ON DATABASE refurbadmin_ai TO refurbadmin;
   ```

3. **Update `.env`:**
   ```ini
   DATABASE_URL=postgresql+asyncpg://refurbadmin:secure-password@localhost:5432/refurbadmin_ai
   APP_ENV=production
   DEBUG=False
   ```

4. **Run with production settings:**
   ```batch
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

### Running as Windows Service

Use NSSM (Non-Sucking Service Manager):

```batch
nssm install RefurbAdminAI
nssm set RefurbAdminAI Application "C:\path\to\.venv\Scripts\python.exe"
nssm set RefurbAdminAI Arguments "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
nssm set RefurbAdminAI AppDirectory "C:\path\to\pricing_tool_est"
nssm start RefurbAdminAI
```

---

## 🇿🇦 South African Context

### Compliance

- **POPIA** - Customer PII encrypted at rest using Fernet encryption
- **Currency** - All prices in ZAR (R)
- **Timezone** - SAST (Africa/Johannesburg)
- **Business Hours** - 08:00 - 17:00 SAST

### Local Market Integration

The pricing engine is designed for South African retailers:
- PriceCheck.co.za
- Takealot.com
- Gumtree.co.za

### Contact Information Format

```
South African Phone: +27 12 345 6789
Addresses: Johannesburg, Gauteng, South Africa
```

---

## 📝 License

Proprietary - RefurbAdmin AI © 2026

---

## 🤝 Support

For issues and questions:
- API Documentation: http://localhost:8000/docs
- Logs: `data/logs/refurbadmin.log`

---

**Built with ❤️ for South African IT Refurbishment**
