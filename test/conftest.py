"""
Pytest configuration and fixtures for integration tests.

This module provides fixtures that manage docker-compose lifecycle
and create HTTP clients for testing the microservices.
"""
import pytest
import subprocess
import time
import httpx
import os
from typing import Generator


# Service port mappings
SERVICES = {
    "dependency-service": "http://localhost:8001",
    "verification-service": "http://localhost:8002",
    "pdf-service": "http://localhost:8003",
    "latex-service": "http://localhost:8004",
}


@pytest.fixture(scope="session")
def docker_compose():
    """
    Use existing docker-compose instance or start a new one for the test session.
    
    This fixture checks if services are already running using docker compose ps.
    If so, it uses the existing instance and does not tear it down. If services
    are not running, it starts docker-compose with --build and tears it down
    after tests complete.
    """
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if services are already running using docker compose ps
    print("\n=== Checking for running docker-compose services ===")
    ps_result = subprocess.run(
        ["docker", "compose", "ps", "--status", "running", "--format", "json"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    
    services_already_running = (ps_result.returncode == 0 and
                                ps_result.stdout.strip() and
                                (len(ps_result.stdout.strip()) > 0))
    
    if services_already_running:
        print("=== Using existing docker-compose instance ===")
        yield
        print("\n=== Keeping existing docker-compose instance running ===")
        return
    
    # Services not running, start them
    print("=== Starting docker-compose ===")
    
    # Stop any existing containers
    subprocess.run(
        ["docker", "compose", "down"],
        cwd=project_root,
        capture_output=True,
    )
    
    # Start docker-compose with build
    result = subprocess.run(
        ["docker", "compose", "up", "--build", "-d"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"Error starting docker-compose: {result.stderr}")
        raise RuntimeError(f"Failed to start docker-compose: {result.stderr}")
    
    print("=== Docker-compose started successfully ===")
    
    # Wait for services to be healthy
    max_attempts = 60  # 60 attempts * 2 seconds = 2 minutes max wait
    attempt = 0
    
    print("=== Waiting for services to become healthy ===")
    
    while attempt < max_attempts:
        try:
            # Check if all services are healthy
            all_healthy = True
            
            for service_name, base_url in SERVICES.items():
                try:
                    response = httpx.get(f"{base_url}/health", timeout=2.0)
                    if response.status_code != 200:
                        all_healthy = False
                        print(f"  {service_name}: not ready (status {response.status_code})")
                        break
                    else:
                        print(f"  {service_name}: healthy")
                except (httpx.ConnectError, httpx.TimeoutException):
                    all_healthy = False
                    print(f"  {service_name}: not reachable")
                    break
            
            if all_healthy:
                print("=== All services are healthy ===")
                break
                
        except Exception as e:
            print(f"Error checking health: {e}")
        
        attempt += 1
        time.sleep(2)
    
    if attempt >= max_attempts:
        # Print docker-compose logs for debugging
        logs_result = subprocess.run(
            ["docker", "compose", "logs", "--tail=50"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        print(f"=== Docker-compose logs ===\n{logs_result.stdout}")
        
        # Clean up
        subprocess.run(
            ["docker", "compose", "down"],
            cwd=project_root,
            capture_output=True,
        )
        raise RuntimeError("Services did not become healthy in time")
    
    # Yield control to tests
    yield
    
    # Teardown: stop docker-compose (only because we started it)
    print("\n=== Stopping docker-compose (we started it) ===")
    subprocess.run(
        ["docker", "compose", "down"],
        cwd=project_root,
        capture_output=True,
    )
    print("=== Docker-compose stopped ===")


@pytest.fixture
def http_client(docker_compose) -> Generator[httpx.Client, None, None]:
    """
    Provide an httpx.Client for making HTTP requests to services.
    
    This client depends on docker_compose to ensure services are running.
    """
    with httpx.Client(timeout=10.0) as client:
        yield client


@pytest.fixture
def dependency_service_url(docker_compose) -> str:
    """Return the base URL for the dependency service."""
    return SERVICES["dependency-service"]


@pytest.fixture
def verification_service_url(docker_compose) -> str:
    """Return the base URL for the verification service."""
    return SERVICES["verification-service"]


@pytest.fixture
def pdf_service_url(docker_compose) -> str:
    """Return the base URL for the PDF service."""
    return SERVICES["pdf-service"]


@pytest.fixture
def latex_service_url(docker_compose) -> str:
    """Return the base URL for the LaTeX service."""
    return SERVICES["latex-service"]
