"""
RefurbAdmin AI - Price Check API Tests

Tests for the /api/v1/price-check endpoint.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from decimal import Decimal

from app.models.device import Device, DeviceStatus


# =============================================================================
# SUCCESS TESTS
# =============================================================================

class TestPriceCheckSuccess:
    """Test successful price check scenarios."""
    
    @pytest.mark.asyncio
    async def test_price_check_valid_device(
        self,
        test_client: AsyncClient,
        test_device: Device,
    ):
        """Test price check with valid ready device."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": test_device.serial_number},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["device"]["serial"] == test_device.serial_number
        assert "pricing" in data
        assert "client_snippet" in data
        assert "quote_valid_until" in data
        
        # Verify pricing structure
        pricing = data["pricing"]
        assert "base_market_price_zar" in pricing
        assert "final_price_zar" in pricing
        assert "currency" in pricing
        assert pricing["currency"] == "ZAR"
    
    @pytest.mark.asyncio
    async def test_price_check_includes_warranty(
        self,
        test_client: AsyncClient,
        test_device: Device,
    ):
        """Test price check includes warranty information."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={
                "serial_number": test_device.serial_number,
                "include_warranty": True,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pricing"]["warranty_months"] == 3
        assert "warranty" in data["client_snippet"].lower()
    
    @pytest.mark.asyncio
    async def test_price_check_device_info(
        self,
        test_client: AsyncClient,
        test_device: Device,
    ):
        """Test price check returns correct device info."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": test_device.serial_number},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        device_info = data["device"]
        assert device_info["model"] == f"{test_device.make} {test_device.model}"
        assert device_info["inventory_status"] == "ready"
        assert "days_in_stock" in device_info


# =============================================================================
# ERROR TESTS
# =============================================================================

class TestPriceCheckErrors:
    """Test price check error scenarios."""
    
    @pytest.mark.asyncio
    async def test_price_check_device_not_found(
        self,
        test_client: AsyncClient,
    ):
        """Test price check with non-existent serial number."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": "NONEXISTENT123"},
        )
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["detail"]["status"] == "error"
        assert data["detail"]["code"] == "DEVICE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_price_check_ber_device(
        self,
        test_client: AsyncClient,
        test_ber_device: Device,
    ):
        """Test price check with BER device."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": test_ber_device.serial_number},
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert data["detail"]["code"] == "DEVICE_BER"
        assert "BER" in data["detail"]["message"]
    
    @pytest.mark.asyncio
    async def test_price_check_not_ready_device(
        self,
        test_client: AsyncClient,
        test_db,
        sample_device_data,
    ):
        """Test price check with device not in Ready status."""
        # Create device with non-ready status
        device = Device(**sample_device_data)
        device.status = DeviceStatus.DIAGNOSIS
        test_db.add(device)
        await test_db.commit()
        
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": device.serial_number},
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert data["detail"]["code"] == "DEVICE_NOT_READY"


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class TestPriceCheckAuth:
    """Test price check authentication."""
    
    @pytest.mark.asyncio
    async def test_price_check_no_api_key(
        self,
        test_db,
    ):
        """Test price check without API key."""
        from app.main import app
        
        # Create client without API key
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/price-check",
                json={"serial_number": "TEST123"},
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_price_check_invalid_api_key(
        self,
        test_client: AsyncClient,
    ):
        """Test price check with invalid API key."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": "TEST123"},
            headers={"X-API-Key": "invalid-key"},
        )
        
        assert response.status_code == 401


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestPriceCheckValidation:
    """Test price check input validation."""
    
    @pytest.mark.asyncio
    async def test_price_check_empty_serial(
        self,
        test_client: AsyncClient,
    ):
        """Test price check with empty serial number."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": ""},
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_price_check_missing_serial(
        self,
        test_client: AsyncClient,
    ):
        """Test price check with missing serial number."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={},
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_price_check_serial_whitespace(
        self,
        test_client: AsyncClient,
        test_device: Device,
    ):
        """Test price check with whitespace in serial number."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": f"  {test_device.serial_number}  "},
        )
        
        assert response.status_code == 200


# =============================================================================
# GET VARIANT TESTS
# =============================================================================

class TestPriceCheckGetVariant:
    """Test GET variant of price check endpoint."""
    
    @pytest.mark.asyncio
    async def test_price_check_get(
        self,
        test_client: AsyncClient,
        test_device: Device,
    ):
        """Test GET price check."""
        response = await test_client.get(
            f"/api/v1/price-check/{test_device.serial_number}",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["device"]["serial"] == test_device.serial_number


# =============================================================================
# PRICING LOGIC TESTS
# =============================================================================

class TestPricingLogic:
    """Test pricing calculation logic."""
    
    @pytest.mark.asyncio
    async def test_price_check_currency_zar(
        self,
        test_client: AsyncClient,
        test_device: Device,
    ):
        """Test price check uses ZAR currency."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": test_device.serial_number},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pricing"]["currency"] == "ZAR"
    
    @pytest.mark.asyncio
    async def test_price_check_has_client_snippet(
        self,
        test_client: AsyncClient,
        test_device: Device,
    ):
        """Test price check includes client snippet."""
        response = await test_client.post(
            "/api/v1/price-check",
            json={"serial_number": test_device.serial_number},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        snippet = data["client_snippet"]
        assert test_device.serial_number in snippet
        assert "R" in snippet  # Currency symbol
        assert len(snippet) > 20  # Reasonable length
