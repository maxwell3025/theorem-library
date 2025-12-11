"""
Pytest configuration and fixtures for integration tests.

This module provides fixtures that manage docker-compose lifecycle
and create HTTP clients for testing the microservices.
"""

import pytest
import subprocess
import httpx
import os
from typing import Generator


SERVICES = {
    "dependency-service": "http://localhost/dependency-service",
    "verification-service": "http://localhost/verification-service",
    "pdf-service": "http://localhost/pdf-service",
    "latex-service": "http://localhost/latex-service",
}


def are_services_running(project_root: str) -> bool:
    """Check if any docker-compose services are currently running."""
    ps_result = subprocess.run(
        ["docker", "compose", "ps", "--status", "running", "--format", "json"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    return bool(
        ps_result.returncode == 0
        and ps_result.stdout.strip()
        and len(ps_result.stdout.strip()) > 0
    )


@pytest.fixture(scope="session")
def docker_compose():
    """
    Use existing docker-compose instance or start a new one for the test session.

    This fixture checks if services are already running using docker compose ps.
    If so, it uses the existing instance and does not tear it down. If services
    are not running, it starts docker-compose with --build and tears it down
    after tests complete.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    services_already_running = are_services_running(project_root)

    if services_already_running:
        print("=== Using existing docker-compose instance ===")
    else:
        print("=== Starting docker-compose ===")
        subprocess.run(
            ["docker", "compose", "up", "--build", "-d", "--wait"],
            cwd=project_root,
            capture_output=True,
            text=True,
        ).check_returncode()

    yield

    if services_already_running:
        print("\n=== Keeping existing docker-compose instance running ===")
    else:
        print("\n=== Stopping docker-compose ===")
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
