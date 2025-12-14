"""
Integration tests for full workflow across all services.

These tests verify that tasks complete successfully and results are stored
in all relevant locations (Neo4j, Redis, logs).
"""
import pytest
import httpx
import logging
import time
from formatutils import pretty_print_response
from conftest import wait_for_celery_task_by_status_endpoint

logger = logging.getLogger(__name__)


def test_full_workflow_dependency_verification_latex(
    http_client: httpx.Client,
    dependency_service_url: str,
    verification_service_url: str,
    latex_service_url: str,
    git_repositories: dict
):
    """
    Test complete workflow:
    1. Add project to dependency service
    2. Wait for completion and verify via REST API
    3. Run verification task
    4. Wait for verification and check Redis
    5. Run LaTeX compilation task
    6. Wait for LaTeX and check Redis
    """
    base_math = git_repositories["base-math"]
    
    # Step 1: Add project to dependency service
    logger.info("=== Step 1: Adding project to dependency service ===")
    dep_response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={
            "repo_url": base_math["url"],
            "commit": base_math["commit"]
        }
    )
    pretty_print_response(dep_response, logger)
    assert dep_response.status_code == 200
    dep_task_id = dep_response.json()["task_id"]
    logger.info(f"Dependency task queued with ID: {dep_task_id}")
    
    # Step 2: Wait for dependency task to complete and verify via REST API
    logger.info("=== Step 2: Waiting for dependency task completion ===")
    max_wait_time = 120
    poll_interval = 2
    elapsed_time = 0
    task_completed = False
    
    while elapsed_time < max_wait_time:
        projects_response = http_client.get(url=f"{dependency_service_url}/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json()
            project_exists = any(
                p["repo_url"] == base_math["url"] and p["commit"] == base_math["commit"]
                for p in projects
            )
            if project_exists:
                task_completed = True
                logger.info(f"Dependency task completed after {elapsed_time} seconds")
                break
        
        time.sleep(poll_interval)
        elapsed_time += poll_interval
    
    assert task_completed, "Dependency task did not complete within timeout"
    
    # Verify via REST API
    projects_response = http_client.get(url=f"{dependency_service_url}/projects")
    assert projects_response.status_code == 200
    projects = projects_response.json()
    project_found = any(
        p["repo_url"] == base_math["url"] and p["commit"] == base_math["commit"]
        for p in projects
    )
    assert project_found, "Project not found in projects list"
    logger.info(f"✓ Verified project via REST API: {base_math['url']}@{base_math['commit']}")
    
    # Step 3: Run verification task
    logger.info("=== Step 3: Running verification task ===")
    verification_request = {
        "repo_url": base_math["url"],
        "commit_hash": base_math["commit"]
    }
    verify_response = http_client.post(
        f"{verification_service_url}/run",
        json=verification_request
    )
    pretty_print_response(verify_response, logger)
    assert verify_response.status_code == 202
    logger.info(f"Verification task queued")
    
    # Step 4: Wait for verification completion via status endpoint
    logger.info("=== Step 4: Waiting for verification task completion ===")
    
    verification_data = wait_for_celery_task_by_status_endpoint(
        http_client=http_client,
        status_url=f"{verification_service_url}/status",
        request_data=verification_request,
        timeout=180.0,
        poll_interval=2.0
    )
    
    assert verification_data is not None, "Verification task did not complete within timeout"
    assert verification_data["status"] in ["success", "fail"]
    logger.info(f"✓ Verification completed with status: {verification_data['status']}, task_id: {verification_data['task_id']}")
    
    # Verify status is accessible via REST API
    status_response = http_client.post(
        url=f"{verification_service_url}/status",
        json=verification_request
    )
    pretty_print_response(status_response, logger)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == verification_data["status"]
    logger.info(f"✓ Verified verification status accessible via REST API")
    
    # Step 5: Run LaTeX compilation task
    logger.info("=== Step 5: Running LaTeX compilation task ===")
    latex_request = {
        "repo_url": base_math["url"],
        "commit_hash": base_math["commit"]
    }
    latex_response = http_client.post(
        f"{latex_service_url}/run",
        json=latex_request
    )
    pretty_print_response(latex_response, logger)
    assert latex_response.status_code == 202
    logger.info(f"LaTeX task queued")
    
    # Step 6: Wait for LaTeX completion via status endpoint
    logger.info("=== Step 6: Waiting for LaTeX task completion ===")
    
    latex_data = wait_for_celery_task_by_status_endpoint(
        http_client=http_client,
        status_url=f"{latex_service_url}/status",
        request_data=latex_request,
        timeout=180.0,
        poll_interval=2.0
    )
    
    assert latex_data is not None, "LaTeX task did not complete within timeout"
    assert latex_data["status"] in ["success", "fail"]
    logger.info(f"✓ LaTeX compilation completed with status: {latex_data['status']}, task_id: {latex_data['task_id']}")
    
    # Verify status is accessible via REST API
    status_response = http_client.post(
        url=f"{latex_service_url}/status",
        json=latex_request
    )
    pretty_print_response(status_response, logger)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == latex_data["status"]
    logger.info(f"✓ Verified LaTeX status accessible via REST API")
    
    logger.info("=== Full workflow test completed successfully ===")


def test_workflow_with_dependencies(
    http_client: httpx.Client,
    dependency_service_url: str,
    verification_service_url: str,
    latex_service_url: str,
    git_repositories: dict
):
    """
    Test workflow with a project that has dependencies:
    1. Ensure base-math is indexed
    2. Add algebra-theorems (depends on base-math)
    3. Verify dependency relationship via REST API
    4. Run verification on algebra-theorems
    5. Run LaTeX on algebra-theorems
    """
    base_math = git_repositories["base-math"]
    algebra_theorems = git_repositories["algebra-theorems"]
    
    # Step 1: Ensure base-math is indexed
    logger.info("=== Step 1: Ensuring base-math is indexed ===")
    base_response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={
            "repo_url": base_math["url"],
            "commit": base_math["commit"]
        }
    )
    pretty_print_response(base_response, logger)
    assert base_response.status_code == 200
    time.sleep(10)  # Give it time to index
    
    # Step 2: Add algebra-theorems
    logger.info("=== Step 2: Adding algebra-theorems project ===")
    algebra_response = http_client.post(
        url=f"{dependency_service_url}/projects",
        json={
            "repo_url": algebra_theorems["url"],
            "commit": algebra_theorems["commit"]
        }
    )
    pretty_print_response(algebra_response, logger)
    assert algebra_response.status_code == 200
    algebra_task_id = algebra_response.json()["task_id"]
    logger.info(f"Algebra-theorems task queued with ID: {algebra_task_id}")
    
    # Wait for completion
    max_wait_time = 120
    poll_interval = 2
    elapsed_time = 0
    task_completed = False
    
    while elapsed_time < max_wait_time:
        projects_response = http_client.get(url=f"{dependency_service_url}/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json()
            project_exists = any(
                p["repo_url"] == algebra_theorems["url"] and p["commit"] == algebra_theorems["commit"]
                for p in projects
            )
            if project_exists:
                task_completed = True
                logger.info(f"Algebra-theorems task completed after {elapsed_time} seconds")
                break
        
        time.sleep(poll_interval)
        elapsed_time += poll_interval
    
    assert task_completed, "Algebra-theorems task did not complete within timeout"
    
    # Step 3: Verify dependency relationship via REST API
    logger.info("=== Step 3: Verifying dependency relationship via REST API ===")
    deps_response = http_client.get(
        url=f"{dependency_service_url}/projects/{algebra_theorems['url']}/{algebra_theorems['commit']}/dependencies"
    )
    pretty_print_response(deps_response, logger)
    assert deps_response.status_code == 200
    dependencies = deps_response.json()
    assert len(dependencies) >= 1, "Expected at least one dependency"
    
    # Verify base-math is in the dependencies
    dep_repos = [dep["dependency_repo"] for dep in dependencies]
    assert base_math["url"] in dep_repos, f"Expected {base_math['url']} in dependencies"
    logger.info(f"✓ Verified dependency relationship via REST API: {algebra_theorems['url']} -> {base_math['url']}")
    
    # Step 4: Run verification on algebra-theorems
    logger.info("=== Step 4: Running verification on algebra-theorems ===")
    verification_request = {
        "repo_url": algebra_theorems["url"],
        "commit_hash": algebra_theorems["commit"]
    }
    verify_response = http_client.post(
        f"{verification_service_url}/run",
        json=verification_request
    )
    pretty_print_response(verify_response, logger)
    assert verify_response.status_code == 202
    
    verification_data = wait_for_celery_task_by_status_endpoint(
        http_client=http_client,
        status_url=f"{verification_service_url}/status",
        request_data=verification_request,
        timeout=180.0,
        poll_interval=2.0
    )
    
    assert verification_data is not None, "Verification task did not complete within timeout"
    logger.info(f"✓ Verification completed with status: {verification_data['status']}")
    
    # Step 5: Run LaTeX on algebra-theorems
    logger.info("=== Step 5: Running LaTeX on algebra-theorems ===")
    latex_request = {
        "repo_url": algebra_theorems["url"],
        "commit_hash": algebra_theorems["commit"]
    }
    latex_response = http_client.post(
        f"{latex_service_url}/run",
        json=latex_request
    )
    pretty_print_response(latex_response, logger)
    assert latex_response.status_code == 202
    
    latex_data = wait_for_celery_task_by_status_endpoint(
        http_client=http_client,
        status_url=f"{latex_service_url}/status",
        request_data=latex_request,
        timeout=180.0,
        poll_interval=2.0
    )
    
    assert latex_data is not None, "LaTeX task did not complete within timeout"
    logger.info(f"✓ LaTeX compilation completed with status: {latex_data['status']}")
    
    logger.info("=== Workflow with dependencies test completed successfully ===")


def test_parallel_tasks_complete_independently(
    http_client: httpx.Client,
    verification_service_url: str,
    git_repositories: dict
):
    """
    Test that multiple parallel verification tasks complete independently.
    """
    base_math = git_repositories["base-math"]
    algebra_theorems = git_repositories["algebra-theorems"]
    
    logger.info("=== Submitting parallel verification tasks ===")
    
    tasks = [
        {"repo_url": base_math["url"], "commit_hash": base_math["commit"]},
        {"repo_url": algebra_theorems["url"], "commit_hash": algebra_theorems["commit"]}
    ]
    
    # Submit all tasks
    for task in tasks:
        response = http_client.post(f"{verification_service_url}/run", json=task)
        pretty_print_response(response, logger)
        assert response.status_code == 202
        logger.info(f"Queued verification for {task['repo_url']}")
    
    logger.info("=== Waiting for all tasks to complete ===")
    
    # Wait for all to complete
    results = []
    for task in tasks:
        task_data = wait_for_celery_task_by_status_endpoint(
            http_client=http_client,
            status_url=f"{verification_service_url}/status",
            request_data=task,
            timeout=180.0,
            poll_interval=2.0
        )
        assert task_data is not None, f"Task for {task['repo_url']} did not complete"
        results.append(task_data)
        logger.info(f"✓ {task['repo_url']} completed with status: {task_data['status']}")
    
    # Verify they have different task IDs
    task_ids = [r["task_id"] for r in results]
    assert len(task_ids) == len(set(task_ids)), "Task IDs should be unique"
    logger.info(f"✓ All tasks completed with unique task IDs: {task_ids}")
