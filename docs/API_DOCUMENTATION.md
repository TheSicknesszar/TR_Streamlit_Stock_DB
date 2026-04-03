# RefurbAdmin AI - API Documentation

Complete API documentation for RefurbAdmin AI inventory and pricing management system.

## Base URL

```
Production: https://api.refurbadmin.co.za/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

All API requests require authentication using Bearer tokens.

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.refurbadmin.co.za/api/v1/products
```

## Rate Limiting

| Tier | Requests/Minute | Requests/Hour | Burst |
|------|-----------------|---------------|-------|
| Standard | 60 | 1,000 | 10 |
| Premium | 200 | 5,000 | 30 |
| Enterprise | 1,000 | 50,000 | 100 |

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Seconds until limit resets

## Endpoints

### Authentication

#### POST /auth/login
```json
{
  "email": "user@example.co.za",
  "password": "SecurePassword123!"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### POST /auth/register
```json
{
  "email": "user@example.co.za",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+27821234567"
}
```

### Products

#### GET /products
List all products with pagination.

Query Parameters:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `category`: Filter by category
- `search`: Search by name or SKU

#### POST /products
Create a new product.

```json
{
  "name": "Samsung 55\" TV",
  "sku": "TV-SAM-55-001",
  "serial_number": "ABC12345678",
  "category": "Electronics",
  "cost_price": 3500.00,
  "selling_price": 5500.00,
  "quantity": 10,
  "condition": "refurbished"
}
```

#### GET /products/{id}
Get product details.

#### PUT /products/{id}
Update product.

#### DELETE /products/{id}
Delete product.

### Inventory

#### GET /inventory
Get inventory status.

#### POST /inventory/adjust
Adjust inventory levels.

```json
{
  "product_id": 123,
  "adjustment": -5,
  "reason": "damaged",
  "notes": "Screen cracked during handling"
}
```

### Quotes

#### POST /quotes/request
Request a quote (public endpoint).

```json
{
  "customer_name": "John Doe",
  "customer_email": "john@example.co.za",
  "customer_phone": "+27821234567",
  "items": [
    {"product_id": 1, "quantity": 2}
  ],
  "notes": "Delivery required"
}
```

#### GET /quotes
List quotes (authenticated).

#### POST /quotes/{id}/accept
Accept a quote.

### Pricing

#### GET /pricing/calculate
Calculate optimal pricing.

Query Parameters:
- `product_id`: Product to price
- `competitor_data`: JSON encoded competitor prices
- `margin_target`: Target margin percentage

### Reports

#### GET /reports/inventory
Generate inventory report.

#### GET /reports/sales
Generate sales report.

Query Parameters:
- `start_date`: Report start date
- `end_date`: Report end date
- `format`: pdf, xlsx, csv

### Admin

#### GET /admin/users
List all users (admin only).

#### POST /admin/users
Create new user (admin only).

#### GET /admin/audit-logs
View audit logs (admin only).

## Error Responses

### 400 Bad Request
```json
{
  "error": "validation_error",
  "message": "Invalid input data",
  "details": [
    {"field": "email", "message": "Invalid email format"}
  ]
}
```

### 401 Unauthorized
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "error": "forbidden",
  "message": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "message": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "request_id": "req_123456"
}
```

## Webhooks

Configure webhooks to receive real-time notifications:

### Events
- `quote.created`
- `quote.accepted`
- `sale.completed`
- `inventory.low_stock`
- `repair.status_changed`

### Webhook Payload
```json
{
  "event": "quote.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "quote_id": "QT-2024-001",
    "customer_email": "customer@example.co.za",
    "total": 5500.00
  }
}
```

## South African Compliance

### POPIA
All endpoints handling personal data are logged for POPIA compliance.

### Currency
All prices are in South African Rand (ZAR/R).

### Phone Numbers
Phone numbers should be in international format: +27XXXXXXXXX

## Support

- Email: api-support@refurbadmin.co.za
- Phone: 0800 REFURB
- Documentation: https://docs.refurbadmin.co.za
