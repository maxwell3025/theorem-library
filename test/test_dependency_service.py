"""
Tests for the dependency service endpoints.
"""
import pytest
import httpx


def test_health_check(http_client: httpx.Client, dependency_service_url: str):
    """Test that the dependency service health check endpoint returns healthy status."""
    response = http_client.get(f"{dependency_service_url}/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "healthy"
    assert "dependencies" in data
    assert "postgres" in data["dependencies"]


def test_health_check_has_correlation_id(http_client: httpx.Client, dependency_service_url: str):
    """Test that health check responses include X-Correlation-ID header."""
    response = http_client.get(f"{dependency_service_url}/health")
    
    assert "X-Correlation-ID" in response.headers


def test_health_check_with_custom_correlation_id(http_client: httpx.Client, dependency_service_url: str):
    """Test that custom correlation IDs are preserved in responses."""
    correlation_id = "test-correlation-id-123"
    response = http_client.get(
        f"{dependency_service_url}/health",
        headers={"X-Correlation-ID": correlation_id}
    )
    
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == correlation_id
