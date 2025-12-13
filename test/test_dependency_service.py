import pytest
import httpx
import logging
from formatutils import pretty_print_response

logger = logging.getLogger(__name__)


def test_health_check(http_client: httpx.Client, dependency_service_url: str):
    """Test that the dependency service health check endpoint returns healthy status."""
    response = http_client.get(url=f"{dependency_service_url}/health")
    pretty_print_response(response, logger)
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    data = response.json()
    assert data["status"] == "healthy"
