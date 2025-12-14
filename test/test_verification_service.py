import pytest
import httpx
import logging
from formatutils import pretty_print_response
from conftest import wait_for_celery_task_by_status_endpoint

logger = logging.getLogger(__name__)


def test_health_check(http_client: httpx.Client, verification_service_url: str):
    """Test that the verification service health check endpoint returns healthy status."""
    response = http_client.get(f"{verification_service_url}/health")
    pretty_print_response(response, logger)
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    data = response.json()
    assert data["status"] == "healthy"


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
    assert data["status"] == "queued"
    assert data["repo_url"] == request_data["repo_url"]
    assert data["commit_hash"] == request_data["commit_hash"]


def test_get_task_status(http_client: httpx.Client, verification_service_url: str):
    """Test that the status endpoint returns task information."""
    repo_url = "https://github.com/test/repo"
    commit_hash = "abc123def456"

    run_response = http_client.post(
        url=f"{verification_service_url}/run",
        json={
            "repo_url": repo_url,
            "commit_hash": commit_hash,
        },
    )
    pretty_print_response(run_response, logger)
    assert run_response.status_code == 202
    run_data = run_response.json()
    assert repo_url == run_data["repo_url"]
    assert commit_hash == run_data["commit_hash"]

    status_response = http_client.post(
        url=f"{verification_service_url}/status",
        json={
            "repo_url": repo_url,
            "commit_hash": commit_hash,
        },
    )
    pretty_print_response(status_response, logger)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["repo_url"] == repo_url
    assert status_data["commit_hash"] == commit_hash
    assert status_data["status"] in ["queued", "running", "success", "fail"]
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
    assert data["status"] == "not_found"
    assert data["repo_url"] == fake_repo_url
    assert data["commit_hash"] == fake_commit_hash


def test_run_verification_missing_body(
    http_client: httpx.Client, verification_service_url: str
):
    """Test that the run endpoint requires a request body."""
    response = http_client.post(f"{verification_service_url}/run")
    pretty_print_response(response, logger)
    assert response.status_code == 422


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


def test_verification_queue_completion_via_status_endpoint(
    http_client: httpx.Client, verification_service_url: str, git_repositories: dict
):
    """Test waiting for verification task completion using status endpoint polling."""
    algebra_theorems = git_repositories["algebra-theorems"]

    # Submit verification task
    request_data = {
        "repo_url": algebra_theorems["url"],
        "commit_hash": algebra_theorems["commit"],
    }
    response = http_client.post(f"{verification_service_url}/run", json=request_data)
    pretty_print_response(response, logger)
    assert response.status_code == 202
    logger.info(
        f"Verification task queued for {algebra_theorems['url']}@{algebra_theorems['commit']}"
    )

    # Wait for completion using status endpoint
    status_data = wait_for_celery_task_by_status_endpoint(
        http_client=http_client,
        status_url=f"{verification_service_url}/status",
        request_data=request_data,
        timeout=180.0,
        poll_interval=2.0,
    )

    assert status_data is not None, "Verification task did not complete within timeout"
    assert status_data["status"] in ["success", "fail"]
    assert status_data["task_id"] is not None
    assert status_data["repo_url"] == algebra_theorems["url"]
    assert status_data["commit_hash"] == algebra_theorems["commit"]
    logger.info(
        f"Task completed with status: {status_data['status']}, task_id: {status_data['task_id']}"
    )
