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
    assert "redis" in data["dependencies"]


def test_health_check_has_correlation_id(
    http_client: httpx.Client, verification_service_url: str
):
    """Test that health check responses include X-Correlation-ID header."""
    response = http_client.get(f"{verification_service_url}/health")
    pretty_print_response(response, logger)

    assert "X-Correlation-ID" in response.headers


def test_run_verification(http_client: httpx.Client, verification_service_url: str):
    """Test that the verification run endpoint queues a task."""
    request_data = {
        "repo_url": "https://github.com/test/repo",
        "commit_hash": "abc123def456",
    }
    response = http_client.post(f"{verification_service_url}/run", json=request_data)
    pretty_print_response(response, logger)

    assert response.status_code == 202
    data = response.json()

    assert "repo_url" in data
    assert "commit_hash" in data
    assert "status" in data
    assert data["status"] == "queued"
    assert data["repo_url"] == request_data["repo_url"]
    assert data["commit_hash"] == request_data["commit_hash"]


def test_get_task_status(http_client: httpx.Client, verification_service_url: str):
    """Test that the status endpoint returns task information."""
    # First, queue a task
    request_data = {
        "repo_url": "https://github.com/test/repo",
        "commit_hash": "xyz789abc123",
    }
    run_response = http_client.post(
        f"{verification_service_url}/run", json=request_data
    )
    pretty_print_response(run_response, logger)

    assert run_response.status_code == 202
    run_data = run_response.json()
    repo_url = run_data["repo_url"]
    commit_hash = run_data["commit_hash"]

    # Then, check its status
    status_response = http_client.post(
        f"{verification_service_url}/status",
        json={"repo_url": repo_url, "commit_hash": commit_hash},
    )
    pretty_print_response(status_response, logger)

    assert status_response.status_code == 200
    status_data = status_response.json()

    assert "repo_url" in status_data
    assert status_data["repo_url"] == repo_url
    assert "commit_hash" in status_data
    assert status_data["commit_hash"] == commit_hash
    assert "status" in status_data
    assert status_data["status"] in ["queued", "running", "success", "fail"]
    assert "task_id" in status_data
    assert status_data["task_id"] is not None


def test_get_nonexistent_task_status(
    http_client: httpx.Client, verification_service_url: str
):
    """Test that querying a nonexistent task returns not_found status."""
    fake_repo_url = "https://github.com/fake/nonexistent"
    fake_commit_hash = "nonexistent123456"
    response = http_client.post(
        f"{verification_service_url}/status",
        json={"repo_url": fake_repo_url, "commit_hash": fake_commit_hash},
    )
    pretty_print_response(response, logger)

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "not_found"
    assert "repo_url" in data
    assert data["repo_url"] == fake_repo_url
    assert "commit_hash" in data
    assert data["commit_hash"] == fake_commit_hash


def test_run_verification_missing_body(
    http_client: httpx.Client, verification_service_url: str
):
    """Test that the run endpoint requires a request body."""
    response = http_client.post(f"{verification_service_url}/run")
    pretty_print_response(response, logger)

    assert response.status_code == 422  # Unprocessable Entity


def test_run_verification_missing_fields(
    http_client: httpx.Client, verification_service_url: str
):
    """Test that the run endpoint requires both repo_url and commit_hash."""
    # Missing commit_hash
    response = http_client.post(
        f"{verification_service_url}/run",
        json={"repo_url": "https://github.com/test/repo"},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 422

    # Missing repo_url
    response = http_client.post(
        f"{verification_service_url}/run", json={"commit_hash": "abc123"}
    )
    pretty_print_response(response, logger)
    assert response.status_code == 422
