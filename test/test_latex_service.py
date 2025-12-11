"""
Tests for the LaTeX service endpoints.
"""
import pytest
import httpx


def test_health_check(http_client: httpx.Client, latex_service_url: str):
    """Test that the LaTeX service health check endpoint returns healthy status."""
    response = http_client.get(f"{latex_service_url}/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "healthy"
    assert "dependencies" in data
    
    # LaTeX service depends on postgres
    assert "postgres" in data["dependencies"]


def test_health_check_has_correlation_id(http_client: httpx.Client, latex_service_url: str):
    """Test that health check responses include X-Correlation-ID header."""
    response = http_client.get(f"{latex_service_url}/health")
    
    assert "X-Correlation-ID" in response.headers


def test_health_check_with_custom_correlation_id(http_client: httpx.Client, latex_service_url: str):
    """Test that custom correlation IDs are preserved in responses."""
    correlation_id = "test-latex-correlation-123"
    response = http_client.get(
        f"{latex_service_url}/health",
        headers={"X-Correlation-ID": correlation_id}
    )
    
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == correlation_id
