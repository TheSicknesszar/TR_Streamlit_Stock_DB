# RefurbAdmin AI - Quick Start Guide

## Getting Started in 5 Minutes

### Step 1: Run the Application

Double-click `run_app.bat` or run from command prompt:

```batch
cd C:\Users\User\Documents\pricing_tool_est
run_app.bat
```

The batch file will:
1. ✅ Check Python installation
2. ✅ Create virtual environment (`.venv`)
3. ✅ Install all dependencies
4. ✅ Create `.env` configuration file
5. ✅ Create data directories
6. ✅ Start the FastAPI server

### Step 2: Access API Documentation

Once the server starts, open your browser:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

### Step 3: Test the Price Check Endpoint

#### Option A: Using Swagger UI

1. Go to http://localhost:8000/docs
2. Click on `POST /api/v1/price-check`
3. Click "Try it out"
4. Enter request body:
   ```json
   {
     "serial_number": "TEST123"
   }
   ```
5. Click "Execute"

#### Option B: Using curl

```batch
# First, create a test device
curl -X POST http://localhost:8000/api/v1/inventory ^
  -H "X-API-Key: test-api-key-12345" ^
  -H "Content-Type: application/json" ^
  -d "{\"serial_number\":\"TEST123\",\"make\":\"Dell\",\"model\":\"Inspiron 3580\",\"processor\":\"i5-8265U\",\"ram_gb\":8,\"ssd_gb\":256,\"condition_grade\":\"Grade A\",\"status\":\"Ready\",\"cost_price\":4500.00}"

# Then get pricing
curl -X POST http://localhost:8000/api/v1/price-check ^
  -H "X-API-Key: test-api-key-12345" ^
  -H "Content-Type: application/json" ^
  -d "{\"serial_number\":\"TEST123\"}"
```

#### Option C: Using Python

```python
import requests

# Create a test device
device_data = {
    "serial_number": "TEST123",
    "make": "Dell",
    "model": "Inspiron 3580",
    "processor": "i5-8265U",
    "ram_gb": 8,
    "ssd_gb": 256,
    "condition_grade": "Grade A",
    "status": "Ready",
    "cost_price": 4500.00
}

response = requests.post(
    "http://localhost:8000/api/v1/inventory",
    headers={"X-API-Key": "test-api-key-12345"},
    json=device_data
)
print(f"Device created: {response.json()}")

# Get pricing
price_request = {"serial_number": "TEST123"}
response = requests.post(
    "http://localhost:8000/api/v1/price-check",
    headers={"X-API-Key": "test-api-key-12345"},
    json=price_request
)
print(f"Price: {response.json()}")
```

### Step 4: Run Tests

```batch
# Activate virtual environment
.venv\Scripts\activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api/test_price_check.py -v
```

## Common Issues

### Python Not Found

**Error:** `Python is not installed or not in PATH`

**Solution:**
1. Download Python 3.11+ from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart command prompt and try again

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
1. Find and kill the process using port 8000:
   ```batch
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```
2. Or use a different port by editing `run_app.bat`

### Dependency Installation Fails

**Error:** `Failed to build wheel for...`

**Solution:**
```batch
# Upgrade pip
.venv\Scripts\activate
python -m pip install --upgrade pip

# Install Microsoft C++ Build Tools (for some packages)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

### Database Errors

**Error:** `database is locked` (SQLite)

**Solution:**
1. Stop the application (Ctrl+C)
2. Delete the database file:
   ```batch
   del data\refurbadmin_dev.db
   ```
3. Restart the application

## Next Steps

1. **Review Configuration:** Edit `.env` file with your settings
2. **Create API Keys:** Use the API to create production API keys
3. **Import Inventory:** Add your device inventory via the API
4. **Configure Scrapers:** Set up market data scrapers for your region
5. **Deploy to Production:** Follow the deployment guide in README.md

## Support

- **API Documentation:** http://localhost:8000/docs
- **Logs:** `data/logs/refurbadmin.log`
- **Database:** `data/refurbadmin_dev.db`

---

**RefurbAdmin AI** - Built for South African IT Refurbishment 🇿🇦
