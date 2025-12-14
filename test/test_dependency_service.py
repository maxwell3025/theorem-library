import pytest
import httpx
import logging
import time
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


def test_list_projects(http_client: httpx.Client, dependency_service_url: str):
    """Test listing all projects in the database."""
    response = http_client.get(url=f"{dependency_service_url}/projects")
    pretty_print_response(response, logger)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Each project should have required fields
    for project in data:
        assert "repo_url" in project
        assert "commit" in project


def test_add_project(
    http_client: httpx.Client, dependency_service_url: str, git_repositories: dict
):
    """Test adding a project by cloning its repository."""
    base_math = git_repositories["base-math"]
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": base_math["url"], "commit": base_math["commit"]},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert data["status"] == "queued"
    assert isinstance(data["task_id"], str)
    assert len(data["task_id"]) > 0


def test_add_project_missing_repo_url(
    http_client: httpx.Client, dependency_service_url: str
):
    """Test that adding a project requires repo_url."""
    response = http_client.post(url=f"{dependency_service_url}/projects", json={})
    pretty_print_response(response, logger)
    assert response.status_code == 422  # Unprocessable Entity


def test_add_project_missing_commit(
    http_client: httpx.Client, dependency_service_url: str
):
    """Test that adding a project requires commit."""
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": "https://github.com/test/test-repo"},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 422  # Unprocessable Entity


def test_get_project_dependencies(
    http_client: httpx.Client, dependency_service_url: str
):
    """Test getting dependencies for a specific project."""
    # First, get list of projects
    projects_response = http_client.get(url=f"{dependency_service_url}/projects")
    projects = projects_response.json()

    if len(projects) > 0:
        # Test with first project
        project = projects[0]
        repo_url = project["repo_url"]
        commit = project["commit"]
        response = http_client.get(
            url=f"{dependency_service_url}/projects/{repo_url}/{commit}/dependencies"
        )
        pretty_print_response(response, logger)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for dep in data:
            assert "source_repo" in dep
            assert "source_commit" in dep
            assert "dependency_repo" in dep
            assert "dependency_commit" in dep
            assert dep["source_repo"] == repo_url
            assert dep["source_commit"] == commit


def test_add_dependency_missing_source_project(
    http_client: httpx.Client, dependency_service_url: str
):
    """Test that adding a dependency with non-existent source project returns 404."""
    response = http_client.post(
        url=f"{dependency_service_url}/dependencies",
        json={
            "source_repo": "https://github.com/test/nonexistent-source",
            "source_commit": "abc123",
            "dependency_repo": "https://github.com/test/dep",
            "dependency_commit": "def456",
        },
    )
    pretty_print_response(response, logger)
    assert response.status_code == 404


def test_add_dependency_missing_destination_project(
    http_client: httpx.Client, dependency_service_url: str
):
    """Test that adding a dependency with non-existent destination project returns 404."""
    # First, add a source project
    add_response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": "https://github.com/test/source-project", "commit": "abc123"},
    )
    assert add_response.status_code == 200

    # Wait a bit for the task to process
    time.sleep(2)

    # Try to add dependency to non-existent destination
    response = http_client.post(
        url=f"{dependency_service_url}/dependencies",
        json={
            "source_repo": "https://github.com/test/source-project",
            "source_commit": "abc123",
            "dependency_repo": "https://github.com/test/nonexistent-dest",
            "dependency_commit": "def456",
        },
    )
    pretty_print_response(response, logger)
    assert response.status_code == 404


def test_add_dependency_missing_fields(
    http_client: httpx.Client, dependency_service_url: str
):
    """Test that dependency endpoints validate required fields."""
    # Missing source_repo
    response = http_client.post(
        url=f"{dependency_service_url}/dependencies",
        json={
            "source_commit": "abc123",
            "dependency_repo": "https://github.com/test/dep",
            "dependency_commit": "def456",
        },
    )
    pretty_print_response(response, logger)
    assert response.status_code == 422

    # Missing dependency_commit
    response = http_client.post(
        url=f"{dependency_service_url}/dependencies",
        json={
            "source_repo": "https://github.com/test/source",
            "source_commit": "abc123",
            "dependency_repo": "https://github.com/test/dep",
        },
    )
    pretty_print_response(response, logger)
    assert response.status_code == 422


def test_add_project_invalid_url_format(
    http_client: httpx.Client, dependency_service_url: str
):
    """Test adding a project with malformed URL still queues task."""
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": "not-a-valid-url", "commit": "abc123"},
    )
    pretty_print_response(response, logger)
    # Should still accept and queue the task (validation happens in worker)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data


def test_add_interconnected_packages(
    http_client: httpx.Client, dependency_service_url: str, git_repositories: dict
):
    """Test adding interconnected packages with proper dependencies."""
    # Add base-math (no dependencies)
    base_math = git_repositories["base-math"]
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": base_math["url"], "commit": base_math["commit"]},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200

    # Wait for task to process
    time.sleep(3)

    # Add algebra-theorems (depends on base-math)
    algebra_theorems = git_repositories["algebra-theorems"]
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={
            "repo_url": algebra_theorems["url"],
            "commit": algebra_theorems["commit"],
        },
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200

    # Wait for task to process
    time.sleep(3)

    # Add advanced-proofs (depends on both)
    advanced_proofs = git_repositories["advanced-proofs"]
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": advanced_proofs["url"], "commit": advanced_proofs["commit"]},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200

    # Wait for task to process
    time.sleep(3)

    # Verify dependencies for advanced-proofs
    response = http_client.get(
        url=f"{dependency_service_url}/projects/{advanced_proofs['url']}/{advanced_proofs['commit']}/dependencies"
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200
    dependencies = response.json()
    assert len(dependencies) == 2

    # Check that both dependencies are present
    dep_repos = [dep["dependency_repo"] for dep in dependencies]
    assert base_math["url"] in dep_repos
    assert algebra_theorems["url"] in dep_repos


def test_verify_dependency_chain(
    http_client: httpx.Client, dependency_service_url: str, git_repositories: dict
):
    """Test that the dependency chain is properly recorded in the database."""
    algebra_theorems = git_repositories["algebra-theorems"]
    base_math = git_repositories["base-math"]

    # Get dependencies for algebra-theorems
    response = http_client.get(
        url=f"{dependency_service_url}/projects/{algebra_theorems['url']}/{algebra_theorems['commit']}/dependencies"
    )

    if response.status_code == 200:
        dependencies = response.json()
        # Should have exactly one dependency (base-math)
        assert len(dependencies) == 1
        assert dependencies[0]["dependency_repo"] == base_math["url"]
        assert dependencies[0]["dependency_commit"] == base_math["commit"]


def test_dependency_queue_completion_and_storage(
    http_client: httpx.Client, dependency_service_url: str, git_repositories: dict
):
    """Test that dependency task completes and results are stored and accessible via REST API."""
    base_math = git_repositories["base-math"]

    # Submit task to add project
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": base_math["url"], "commit": base_math["commit"]},
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200
    data = response.json()
    task_id = data["task_id"]
    logger.info(f"Task queued with ID: {task_id}")

    # Wait for task to complete (with timeout)
    max_wait_time = 120  # 2 minutes
    poll_interval = 2
    elapsed_time = 0
    task_completed = False

    while elapsed_time < max_wait_time:
        # Check if project is listed (indicates task completed)
        projects_response = http_client.get(url=f"{dependency_service_url}/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json()
            project_exists = any(
                p["repo_url"] == base_math["url"] and p["commit"] == base_math["commit"]
                for p in projects
            )
            if project_exists:
                task_completed = True
                logger.info(f"Task completed after {elapsed_time} seconds")
                break

        time.sleep(poll_interval)
        elapsed_time += poll_interval

    assert task_completed, f"Task did not complete within {max_wait_time} seconds"

    # Verify project is accessible via REST API
    projects_response = http_client.get(url=f"{dependency_service_url}/projects")
    pretty_print_response(projects_response, logger)
    assert projects_response.status_code == 200
    projects = projects_response.json()

    # Find our project in the list
    project_found = None
    for p in projects:
        if p["repo_url"] == base_math["url"] and p["commit"] == base_math["commit"]:
            project_found = p
            break

    assert project_found is not None, "Project not found in projects list"
    assert project_found["repo_url"] == base_math["url"]
    assert project_found["commit"] == base_math["commit"]
    logger.info(f"Verified project via REST API: {project_found}")

    # Verify dependencies endpoint works
    deps_response = http_client.get(
        url=f"{dependency_service_url}/projects/{base_math['url']}/{base_math['commit']}/dependencies"
    )
    pretty_print_response(deps_response, logger)
    assert deps_response.status_code == 200
    dependencies = deps_response.json()
    assert isinstance(dependencies, list)
    logger.info(f"Project has {len(dependencies)} dependencies")


def test_dependency_with_dependencies_stored_correctly(
    http_client: httpx.Client, dependency_service_url: str, git_repositories: dict
):
    """Test that project dependencies are correctly stored and accessible via REST API."""
    algebra_theorems = git_repositories["algebra-theorems"]
    base_math = git_repositories["base-math"]

    # Ensure base-math is added first
    http_client.post(
        url=f"{dependency_service_url}/projects",
        json={"repo_url": base_math["url"], "commit": base_math["commit"]},
    )
    time.sleep(5)

    # Add algebra-theorems (depends on base-math)
    response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={
            "repo_url": algebra_theorems["url"],
            "commit": algebra_theorems["commit"],
        },
    )
    pretty_print_response(response, logger)
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    logger.info(f"Task queued with ID: {task_id}")

    # Wait for task to complete
    max_wait_time = 120
    poll_interval = 2
    elapsed_time = 0
    task_completed = False

    while elapsed_time < max_wait_time:
        projects_response = http_client.get(url=f"{dependency_service_url}/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json()
            project_exists = any(
                p["repo_url"] == algebra_theorems["url"]
                and p["commit"] == algebra_theorems["commit"]
                for p in projects
            )
            if project_exists:
                task_completed = True
                logger.info(f"Task completed after {elapsed_time} seconds")
                break

        time.sleep(poll_interval)
        elapsed_time += poll_interval

    assert task_completed, f"Task did not complete within {max_wait_time} seconds"

    # Verify via REST API that dependencies are returned correctly
    deps_response = http_client.get(
        url=f"{dependency_service_url}/projects/{algebra_theorems['url']}/{algebra_theorems['commit']}/dependencies"
    )
    pretty_print_response(deps_response, logger)
    assert deps_response.status_code == 200
    dependencies = deps_response.json()
    assert len(dependencies) >= 1, "Expected at least one dependency"

    # Verify the dependency relationship
    dep_repos = [dep["dependency_repo"] for dep in dependencies]
    assert base_math["url"] in dep_repos, f"Expected {base_math['url']} in dependencies"

    # Find the specific dependency and verify all fields
    base_math_dep = None
    for dep in dependencies:
        if dep["dependency_repo"] == base_math["url"]:
            base_math_dep = dep
            break

    assert base_math_dep is not None, "base-math dependency not found"
    assert base_math_dep["source_repo"] == algebra_theorems["url"]
    assert base_math_dep["source_commit"] == algebra_theorems["commit"]
    assert base_math_dep["dependency_repo"] == base_math["url"]
    assert base_math_dep["dependency_commit"] == base_math["commit"]
    logger.info(f"Verified dependency relationship via REST API: {base_math_dep}")
