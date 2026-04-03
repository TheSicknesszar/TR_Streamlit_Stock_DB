#!/usr/bin/env python3
"""
Load Testing Script for RefurbAdmin AI using Locust.

Features:
- Concurrent user simulation (100+ users)
- Response time measurement
- Request rate monitoring
- Error rate tracking
- Custom business scenarios

Usage:
    # Run with web UI:
    locust -f load_test.py --host=http://localhost:8000
    
    # Run headless:
    locust -f load_test.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 300s
    
    # Run with specific user class:
    locust -f load_test.py --host=http://localhost:8000 --headless -u 50 -r 5 --tags api
    
    Parameters:
    -u: Number of users to simulate
    -r: Spawn rate (users per second)
    -t: Test duration
"""

import random
import json
import time
import logging
from locust import (
    HttpUser,
    task,
    between,
    constant,
    events,
    task_sequence,
    seq_task,
)
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging

# Configure logging
setup_logging("INFO", None)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_sa_email() -> str:
    """Generate a random South African email address."""
    domains = ["gmail.com", "yahoo.co.za", "hotmail.com", "company.co.za", "webmail.co.za"]
    names = ["john", "mary", "sipho", "thabo", "zanele", "pieter", "annika", "michael"]
    surnames = ["smith", "ndlovu", "botha", "van_wyk", "mthembu", "coetzee", "mbeki"]
    
    name = random.choice(names)
    surname = random.choice(surnames)
    domain = random.choice(domains)
    number = random.randint(1, 999)
    
    return f"{name}.{surname}{number}@{domain}"


def generate_sa_phone() -> str:
    """Generate a random South African phone number."""
    prefixes = ["082", "083", "084", "072", "073", "074", "061", "062", "063"]
    prefix = random.choice(prefixes)
    number = "".join([str(random.randint(0, 9)) for _ in range(7)])
    
    return f"{prefix}{number}"


def generate_serial_number() -> str:
    """Generate a random product serial number."""
    letters = "".join([chr(random.randint(65, 90)) for _ in range(3)])
    numbers = "".join([str(random.randint(0, 9)) for _ in range(7)])
    
    return f"{letters}{numbers}"


def generate_product_data() -> dict:
    """Generate random product data."""
    categories = ["Electronics", "Furniture", "Appliances", "Tools", "Office Equipment"]
    brands = ["Samsung", "LG", "Defy", "Koyo", "Tefal", "Bosch", "HP", "Dell"]
    
    return {
        "name": f"{random.choice(brands)} {random.choice(['TV', 'Fridge', 'Laptop', 'Phone', 'Tablet'])} {random.randint(100, 999)}",
        "sku": f"SKU-{random.randint(10000, 99999)}",
        "serial_number": generate_serial_number(),
        "category": random.choice(categories),
        "cost_price": round(random.uniform(500, 5000), 2),
        "selling_price": round(random.uniform(800, 8000), 2),
        "quantity": random.randint(1, 50),
        "condition": random.choice(["refurbished", "like_new", "good", "fair"]),
    }


def generate_quote_data() -> dict:
    """Generate random quote data."""
    return {
        "customer_name": f"Customer {random.randint(1, 1000)}",
        "customer_email": generate_sa_email(),
        "customer_phone": generate_sa_phone(),
        "items": [
            {
                "product_id": random.randint(1, 100),
                "quantity": random.randint(1, 5),
            }
            for _ in range(random.randint(1, 5))
        ],
        "notes": f"Quote request {random.randint(1, 10000)}",
    }


# =============================================================================
# User Behavior Classes
# =============================================================================

class RefurbAdminUser(HttpUser):
    """
    Base user class for RefurbAdmin AI load testing.
    
    Simulates typical user behavior with realistic think times.
    """
    
    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)
    
    # Test data
    user_id: str = None
    access_token: str = None
    refresh_token: str = None
    
    def on_start(self):
        """Called when user starts."""
        # Could perform login here
        pass
    
    def on_stop(self):
        """Called when user stops."""
        # Could perform logout here
        pass


class AnonymousUser(RefurbAdminUser):
    """
    Anonymous user - can access public endpoints only.
    
    Simulates visitors browsing the site without logging in.
    """
    
    weight = 3  # Higher weight = more common
    
    @task(5)
    def view_homepage(self):
        """View the homepage."""
        self.client.get("/")
    
    @task(3)
    def view_products(self):
        """Browse products."""
        self.client.get("/api/products")
    
    @task(2)
    def view_product_detail(self):
        """View a specific product."""
        product_id = random.randint(1, 100)
        self.client.get(f"/api/products/{product_id}")
    
    @task(1)
    def request_quote(self):
        """Request a quote (anonymous)."""
        quote_data = generate_quote_data()
        
        with self.client.post(
            "/api/quotes/request",
            json=quote_data,
            name="/api/quotes/request",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(1)
    def check_health(self):
        """Check API health."""
        self.client.get("/api/health")


class AuthenticatedUser(RefurbAdminUser):
    """
    Authenticated user - can access protected endpoints.
    
    Simulates logged-in users performing business operations.
    """
    
    weight = 2
    
    def on_start(self):
        """Login on start."""
        self.login()
    
    def login(self):
        """Perform login."""
        credentials = {
            "email": generate_sa_email(),
            "password": "TestPassword123!",
        }
        
        response = self.client.post(
            "/api/auth/login",
            json=credentials,
            name="/api/auth/login",
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            
            # Set auth header for subsequent requests
            self.client.headers["Authorization"] = f"Bearer {self.access_token}"
        else:
            # Use a default token for testing
            self.client.headers["Authorization"] = "Bearer test_token"
    
    @task(5)
    def view_dashboard(self):
        """View user dashboard."""
        self.client.get("/api/dashboard")
    
    @task(4)
    def list_inventory(self):
        """List inventory items."""
        self.client.get("/api/inventory")
    
    @task(3)
    def view_inventory_detail(self):
        """View specific inventory item."""
        item_id = random.randint(1, 100)
        self.client.get(f"/api/inventory/{item_id}")
    
    @task(2)
    def search_products(self):
        """Search for products."""
        queries = ["laptop", "phone", "tv", "fridge", "tablet"]
        query = random.choice(queries)
        
        self.client.get(
            f"/api/products/search?q={query}",
            name="/api/products/search",
        )
    
    @task(2)
    def view_quotes(self):
        """View user quotes."""
        self.client.get("/api/quotes")
    
    @task(1)
    def create_quote(self):
        """Create a new quote."""
        quote_data = generate_quote_data()
        
        self.client.post(
            "/api/quotes",
            json=quote_data,
            name="/api/quotes",
        )
    
    @task(1)
    def view_profile(self):
        """View user profile."""
        self.client.get("/api/users/me")


class AdminUser(RefurbAdminUser):
    """
    Admin user - can access admin endpoints.
    
    Simulates administrators managing the system.
    """
    
    weight = 1
    
    def on_start(self):
        """Login as admin."""
        self.login_admin()
    
    def login_admin(self):
        """Perform admin login."""
        credentials = {
            "email": "admin@refurbadmin.co.za",
            "password": "AdminPassword123!",
        }
        
        response = self.client.post(
            "/api/auth/login",
            json=credentials,
            name="/api/auth/login",
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.client.headers["Authorization"] = f"Bearer {self.access_token}"
    
    @task(3)
    def view_admin_dashboard(self):
        """View admin dashboard."""
        self.client.get("/api/admin/dashboard")
    
    @task(2)
    def manage_users(self):
        """Manage users."""
        self.client.get("/api/admin/users")
    
    @task(2)
    def view_analytics(self):
        """View analytics."""
        self.client.get("/api/admin/analytics")
    
    @task(1)
    def manage_inventory(self):
        """Manage inventory."""
        # Create product
        product_data = generate_product_data()
        
        self.client.post(
            "/api/admin/inventory",
            json=product_data,
            name="/api/admin/inventory",
        )
    
    @task(1)
    def view_audit_logs(self):
        """View audit logs."""
        self.client.get("/api/admin/audit-logs")
    
    @task(1)
    def system_health(self):
        """Check system health."""
        self.client.get("/api/admin/health")


# =============================================================================
# API-Specific Load Tests
# =============================================================================

class APILoadTest(HttpUser):
    """
    API-focused load tests.
    
    Tests specific API endpoints with high concurrency.
    """
    
    wait_time = constant(0.1)  # Minimal wait for API testing
    weight = 1
    
    @task(10)
    def test_products_api(self):
        """Test products API endpoints."""
        self.client.get("/api/products")
    
    @task(5)
    def test_inventory_api(self):
        """Test inventory API endpoints."""
        self.client.get("/api/inventory")
    
    @task(3)
    def test_quotes_api(self):
        """Test quotes API endpoints."""
        self.client.get("/api/quotes")
    
    @task(2)
    def test_pricing_api(self):
        """Test pricing API endpoints."""
        self.client.get("/api/pricing/calculate")
    
    @task(1)
    def test_health_api(self):
        """Test health API endpoint."""
        self.client.get("/api/health")


class WriteHeavyLoadTest(HttpUser):
    """
    Write-heavy load tests.
    
    Simulates high write load scenarios.
    """
    
    wait_time = between(0.5, 2)
    weight = 1
    
    @task(5)
    def create_quote(self):
        """Create quotes (write operation)."""
        quote_data = generate_quote_data()
        
        self.client.post(
            "/api/quotes",
            json=quote_data,
            name="/api/quotes [POST]",
        )
    
    @task(3)
    def update_inventory(self):
        """Update inventory (write operation)."""
        item_id = random.randint(1, 100)
        
        update_data = {
            "quantity": random.randint(1, 100),
            "price": round(random.uniform(100, 1000), 2),
        }
        
        self.client.put(
            f"/api/inventory/{item_id}",
            json=update_data,
            name="/api/inventory/{id} [PUT]",
        )
    
    @task(2)
    def create_product(self):
        """Create products (write operation)."""
        product_data = generate_product_data()
        
        self.client.post(
            "/api/products",
            json=product_data,
            name="/api/products [POST]",
        )


# =============================================================================
# Event Handlers
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    logger.info("Load test completed!")
    
    # Print summary
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Failed requests: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Called on each request."""
    if exception:
        logger.warning(f"Request failed: {name} - {exception}")


# =============================================================================
# Performance Benchmarks
# =============================================================================

class PerformanceBenchmark(HttpUser):
    """
    Performance benchmark tests.
    
    Measures specific performance metrics.
    """
    
    wait_time = constant(0)  # No wait for pure benchmarking
    
    @task
    def benchmark_homepage(self):
        """Benchmark homepage response time."""
        self.client.get("/")
    
    @task
    def benchmark_api_products(self):
        """Benchmark products API."""
        self.client.get("/api/products")
    
    @task
    def benchmark_api_health(self):
        """Benchmark health API."""
        self.client.get("/api/health")


# =============================================================================
# Custom Load Test Scenarios
# =============================================================================

class BusinessScenarioTest(HttpUser):
    """
    Business scenario load tests.
    
    Simulates complete business workflows.
    """
    
    wait_time = between(2, 5)
    
    @task
    def complete_quote_workflow(self):
        """Complete quote-to-sale workflow."""
        # 1. Browse products
        self.client.get("/api/products")
        
        # 2. View product details
        product_id = random.randint(1, 50)
        self.client.get(f"/api/products/{product_id}")
        
        # 3. Request quote
        quote_data = generate_quote_data()
        response = self.client.post(
            "/api/quotes/request",
            json=quote_data,
            name="/api/quotes/request",
        )
        
        # 4. Check quote status (if successful)
        if response.status_code == 200:
            quote_id = response.json().get("quote_id")
            if quote_id:
                self.client.get(f"/api/quotes/{quote_id}")


# =============================================================================
# Running Locust Programmatically
# =============================================================================

def run_load_test(
    host: str = "http://localhost:8000",
    users: int = 100,
    spawn_rate: int = 10,
    duration: int = 300,
    output_file: str = "load_test_results.json",
):
    """
    Run load test programmatically.
    
    Args:
        host: Target host URL
        users: Number of concurrent users
        spawn_rate: Users spawned per second
        duration: Test duration in seconds
        output_file: File to save results
    """
    from locust.runners import LocalRunner
    from locust.stats import StatsCSV
    import io
    
    # Create environment
    env = Environment(user_classes=[
        AnonymousUser,
        AuthenticatedUser,
        AdminUser,
        APILoadTest,
    ])
    
    # Create runner
    runner = LocalRunner(env)
    
    # Start load test
    runner.start(user_count=users, spawn_rate=spawn_rate)
    
    # Wait for duration
    logger.info(f"Running load test with {users} users for {duration} seconds")
    time.sleep(duration)
    
    # Stop test
    runner.quit()
    
    # Get results
    stats = env.stats
    
    results = {
        "summary": {
            "total_requests": stats.total.num_requests,
            "failed_requests": stats.total.num_failures,
            "requests_per_second": stats.total.current_rps,
            "avg_response_time_ms": stats.total.avg_response_time,
            "min_response_time_ms": stats.total.min_response_time,
            "max_response_time_ms": stats.total.max_response_time,
        },
        "endpoints": {},
    }
    
    for endpoint in stats.entries:
        results["endpoints"][endpoint.name] = {
            "requests": endpoint.num_requests,
            "failures": endpoint.num_failures,
            "avg_response_time_ms": endpoint.avg_response_time,
        }
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")
    
    return results


if __name__ == "__main__":
    # Run with defaults
    run_load_test(
        host="http://localhost:8000",
        users=100,
        spawn_rate=10,
        duration=60,
    )
