"""
Pytest configuration and fixtures for integration tests.

This module provides fixtures that manage docker-compose lifecycle
and create HTTP clients for testing the microservices.
"""

import pytest
import subprocess
import httpx
import os
import logging
import sys
from typing import Generator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import generate_env
from scripts import generate_compose


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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
    are not running, it generates .env and docker-compose.yml files, then starts
    docker-compose with --build and tears it down after tests complete.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    services_already_running = are_services_running(project_root)

    exception = None
    try:
        if not services_already_running:
            logger.info("Generating .env file")
            sys.argv = [
                "generate_env.py",
                "--output",
                os.path.join(project_root, ".env"),
            ]
            generate_env.main()

            logger.info("Generating docker-compose.yml file")
            sys.argv = [
                "generate_compose.py",
                "--output",
                os.path.join(project_root, "docker-compose.yml"),
            ]
            generate_compose.main()

        if services_already_running:
            logger.info("Using existing docker-compose instance")
        else:
            logger.info("Starting docker-compose")
            subprocess.run(
                ["docker", "compose", "up", "--build", "-d", "--wait"],
                cwd=project_root,
                capture_output=False,
                text=True,
            ).check_returncode()

        yield
    except Exception as e:
        exception = e
    finally:
        if services_already_running:
            logger.info("Keeping existing docker-compose instance running")
        else:
            logger.info("Stopping docker-compose")
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "down",
                    "--volumes",
                    "--remove-orphans",
                    "--rmi",
                    "all",
                ],
                cwd=project_root,
                capture_output=True,
            )
            logger.info("Docker-compose stopped")
        if exception:
            raise exception


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
