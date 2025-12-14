import pytest
import httpx
import time
import logging
from formatutils import pretty_print_response

logger = logging.getLogger(__name__)


def test_health_check(http_client: httpx.Client, latex_service_url: str):
    """Test that the LaTeX service health check endpoint returns healthy status."""
    response = http_client.get(url=f"{latex_service_url}/health")
    pretty_print_response(response, logger)
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    data = response.json()
    assert data["status"] == "healthy"


def test_run_latex_compilation(http_client: httpx.Client, latex_service_url: str):
    """Test that the LaTeX compilation run endpoint queues a task."""
    request_data = {
        "repo_url": "https://github.com/test/latex-repo",
        "commit_hash": "abc123def456",
    }
    response = http_client.post(f"{latex_service_url}/run", json=request_data)
    pretty_print_response(response, logger)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["repo_url"] == request_data["repo_url"]
    assert data["commit_hash"] == request_data["commit_hash"]


def test_get_task_status(http_client: httpx.Client, latex_service_url: str):
    """Test that the status endpoint returns task information."""
    repo_url = "https://github.com/test/latex-repo"
    commit_hash = "abc123def456"

    run_response = http_client.post(
        url=f"{latex_service_url}/run",
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
        url=f"{latex_service_url}/status",
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
    http_client: httpx.Client, latex_service_url: str
):
    """Test that querying a nonexistent task returns not_found status."""
    fake_repo_url = "https://github.com/fake/nonexistent-latex"
    fake_commit_hash = "nonexistent123456"

    response = http_client.post(
        f"{latex_service_url}/status",
        json={"repo_url": fake_repo_url, "commit_hash": fake_commit_hash},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"
    assert data["repo_url"] == fake_repo_url
    assert data["commit_hash"] == fake_commit_hash


def test_run_latex_missing_body(
    http_client: httpx.Client, latex_service_url: str
):
    """Test that the run endpoint requires a request body."""
    response = http_client.post(f"{latex_service_url}/run")
    pretty_print_response(response, logger)
    assert response.status_code == 422


def test_run_latex_missing_fields(
    http_client: httpx.Client, latex_service_url: str
):
    """Test that the run endpoint requires both repo_url and commit_hash."""
    # Missing commit_hash
    response = http_client.post(
        f"{latex_service_url}/run",
        json={"repo_url": "https://github.com/test/latex-repo"},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 422

    # Missing repo_url
    response = http_client.post(
        f"{latex_service_url}/run", json={"commit_hash": "abc123"}
    )
    pretty_print_response(response, logger)
    assert response.status_code == 422


def test_compile_latex_from_git_server(
    http_client: httpx.Client, latex_service_url: str, git_repositories: dict
):
    """Test LaTeX compilation with a real repository from the git server."""
    # Use the base-math repository which should have latex-source/main.tex
    base_math_repo = git_repositories.get("base-math")
    if not base_math_repo:
        pytest.skip("base-math repository not available")

    repo_url = base_math_repo["url"]
    commit_hash = base_math_repo["commit"]

    # Queue the compilation task
    run_response = http_client.post(
        f"{latex_service_url}/run",
        json={"repo_url": repo_url, "commit_hash": commit_hash},
    )
    pretty_print_response(run_response, logger)
    assert run_response.status_code == 202

    # Poll for completion with timeout
    max_attempts = 60  # 60 seconds timeout
    status = None
    for _ in range(max_attempts):
        status_response = http_client.post(
            f"{latex_service_url}/status",
            json={"repo_url": repo_url, "commit_hash": commit_hash},
        )
        assert status_response.status_code == 200
        status_data = status_response.json()
        status = status_data["status"]
        
        if status in ["success", "fail"]:
            break
        
        time.sleep(1)

    pretty_print_response(status_response, logger)
    assert status in ["success", "fail"], f"Task did not complete within timeout. Last status: {status}"
    # Note: We don't assert success because the LaTeX might have compilation errors
    # The important thing is that the task completes


def test_redis_key_uniqueness(http_client: httpx.Client, latex_service_url: str):
    """Test that different repo_url/commit_hash combinations create different tasks."""
    task1 = {
        "repo_url": "https://github.com/test/repo1",
        "commit_hash": "commit1",
    }
    task2 = {
        "repo_url": "https://github.com/test/repo2",
        "commit_hash": "commit2",
    }

    response1 = http_client.post(f"{latex_service_url}/run", json=task1)
    pretty_print_response(response1, logger)
    assert response1.status_code == 202

    response2 = http_client.post(f"{latex_service_url}/run", json=task2)
    pretty_print_response(response2, logger)
    assert response2.status_code == 202

    # Check that both tasks have unique statuses
    status1_response = http_client.post(f"{latex_service_url}/status", json=task1)
    status2_response = http_client.post(f"{latex_service_url}/status", json=task2)

    assert status1_response.status_code == 200
    assert status2_response.status_code == 200

    status1_data = status1_response.json()
    status2_data = status2_response.json()

    # Task IDs should be different
    assert status1_data["task_id"] != status2_data["task_id"]

