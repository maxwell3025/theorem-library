import pytest
import httpx
import logging
from formatutils import pretty_print_response

logger = logging.getLogger(__name__)


def test_git_server_health_check(http_client: httpx.Client, git_server_url: str):
    """Test that the git server health check endpoint returns healthy status."""
    response = http_client.get(url=f"{git_server_url}/health")
    pretty_print_response(response, logger)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "repositories" in data
    assert data["repositories"] >= 3  # Should have at least our 3 test repos


def test_git_server_list_repositories(http_client: httpx.Client, git_server_url: str):
    """Test that the git server can list all repositories."""
    response = http_client.get(url=f"{git_server_url}/repositories")
    pretty_print_response(response, logger)
    assert response.status_code == 200
    data = response.json()
    assert "repositories" in data
    repositories = data["repositories"]
    assert len(repositories) >= 3
    
    # Verify required repositories exist
    repo_names = {repo["name"] for repo in repositories}
    assert "base-math" in repo_names
    assert "algebra-theorems" in repo_names
    assert "advanced-proofs" in repo_names
    
    # Verify each repository has required fields
    for repo in repositories:
        assert "name" in repo
        assert "url" in repo
        assert "commit" in repo
        assert len(repo["commit"]) == 40  # Git commit hashes are 40 hex chars


def test_git_repositories_fixture(git_repositories: dict):
    """Test that the git_repositories fixture works correctly."""
    assert len(git_repositories) >= 3
    assert "base-math" in git_repositories
    assert "algebra-theorems" in git_repositories
    assert "advanced-proofs" in git_repositories
    
    # Verify structure of each repository entry
    for name, repo in git_repositories.items():
        assert repo["name"] == name
        assert "url" in repo
        assert "commit" in repo
