"""
Tests for the verification service endpoints.
"""

import pytest
import httpx
import logging
from formatutils import pretty_print_response

logger = logging.getLogger(__name__)


def test_health_check(http_client: httpx.Client, verification_service_url: str):
    """Test that the verification service health check endpoint returns healthy status."""
    response = http_client.get(f"{verification_service_url}/health")
    pretty_print_response(response, logger)

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"
    assert "dependencies" in data
    assert "postgres" in data["dependencies"]


def test_health_check_has_correlation_id(
    http_client: httpx.Client, verification_service_url: str
):
    """Test that health check responses include X-Correlation-ID header."""
    response = http_client.get(f"{verification_service_url}/health")
    pretty_print_response(response, logger)

    assert "X-Correlation-ID" in response.headers


def test_run_verification(http_client: httpx.Client, verification_service_url: str):
    """Test that the verification run endpoint queues a task."""
    response = http_client.post(f"{verification_service_url}/run")
    pretty_print_response(response, logger)

    assert response.status_code == 200
    data = response.json()

    assert "task_id" in data
    assert "status" in data
    assert data["status"] == "Queued"

    # Task ID should be a non-empty string
    assert isinstance(data["task_id"], str)
    assert len(data["task_id"]) > 0
