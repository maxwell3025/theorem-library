"""
Tests for the PDF service endpoints.
"""

import pytest
import httpx
import logging
from formatutils import pretty_print_response

logger = logging.getLogger(__name__)


def test_health_check(http_client: httpx.Client, pdf_service_url: str):
    """Test that the PDF service health check endpoint returns healthy status."""
    response = http_client.get(f"{pdf_service_url}/health")
    pretty_print_response(response, logger)

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"

    # PDF service should not have postgres dependency
    if "dependencies" in data:
        # If dependencies exist, they should all be healthy
        for dep_name, dep_info in data["dependencies"].items():
            assert dep_info["status"] == "healthy"


def test_health_check_has_correlation_id(
    http_client: httpx.Client, pdf_service_url: str
):
    """Test that health check responses include X-Correlation-ID header."""
    response = http_client.get(f"{pdf_service_url}/health")
    pretty_print_response(response, logger)

    assert "X-Correlation-ID" in response.headers
