#!/usr/bin/env python3
"""
Dependency Task - Dynamically spawned container to parse and index dependencies.

This container:
1. Receives task data via URL and COMMIT_HASH environment variables
2. Clones the Git repository at the specified commit
3. Parses math-dependencies.json and validates against lakefile.toml
4. Stores results in Neo4j
5. Exits with status code
"""

import os
import sys
import logging
import subprocess
import tempfile
import json
from pathlib import Path
import typing
import httpx
import tomli
from common.dependency_service import public_model

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("dependency-task")


SECONDS_PER_MINUTE = 60



def clone_repository(repo_url: str, commit_hash: str, work_dir: Path) -> bool:
    """Clone a Git repository at a specific commit."""
    logger.info(f"Cloning repository {repo_url} at commit {commit_hash}")

    # Clone the repository
    clone_result = subprocess.run(
        args=["git", "clone", repo_url, str(work_dir)],
        capture_output=True,
        text=True,
        timeout=10 * SECONDS_PER_MINUTE,
    )

    logger.debug(f"Git clone stdout: \n{clone_result.stdout}")
    logger.debug(f"Git clone stderr: \n{clone_result.stderr}")

    if clone_result.returncode != 0:
        logger.error(f"Failed to clone repository:\n{clone_result.stderr}")
        return False

    # Checkout the commit
    checkout_result = subprocess.run(
        args=["git", "checkout", commit_hash],
        cwd=str(work_dir),
        capture_output=True,
        text=True,
        timeout=10 * SECONDS_PER_MINUTE,
    )

    logger.debug(f"Git checkout stdout: \n{checkout_result.stdout}")
    logger.debug(f"Git checkout stderr: \n{checkout_result.stderr}")

    if checkout_result.returncode != 0:
        logger.error(
            f"Failed to checkout commit {commit_hash}:\n{checkout_result.stderr}"
        )
        return False

    logger.info(f"Successfully cloned repository at commit {commit_hash}")
    return True


def parse_dependencies_from_repo(
    repo_path: Path, repo_url: str, commit: str
) -> typing.List[public_model.ProjectInfo]:
    """
    Parse dependencies from math-dependencies.json and validate against lakefile.toml for Lean 4 packages.
    Ensures all math dependencies have exact git commits specified in lakefile.toml.
    Raises exceptions if validation fails.
    """
    dependencies = []
    validation_errors = []

    # Parse lakefile.toml to get lakefile dependencies
    lakefile = repo_path / "lakefile.toml"
    lakefile_deps = {}

    if not lakefile.exists():
        raise FileNotFoundError(f"lakefile.toml not found in {repo_path}")

    with open(lakefile, "rb") as f:
        lake_data = tomli.load(f)

        # Extract dependencies from lakefile.toml
        # Lean 4 lakefile.toml has [[require]] sections for each dependency
        lakefile_requires = lake_data.get("require", [])
        for req in lakefile_requires:
            if isinstance(req, dict):
                dep_git = req.get("git")
                dep_rev = req.get("rev")
                if dep_git and dep_rev:
                    lakefile_deps[dep_git] = dep_rev

    # Parse math-dependencies.json
    math_deps_file = repo_path / "math-dependencies.json"

    if not math_deps_file.exists():
        raise FileNotFoundError(f"math-dependencies.json not found in {repo_path}")

    with open(math_deps_file, "r") as f:
        dependency_list = json.load(f)

        for dep in dependency_list:
            dep_git = dep.get("git")
            dep_commit = dep.get("commit")

            # Validate required fields
            if not dep_git:
                validation_errors.append("Dependency missing 'git' field")
                continue

            if not dep_commit:
                validation_errors.append(
                    f"Dependency '{dep_git}' missing 'commit' field"
                )
                continue

            # Validate dependency exists in lakefile.toml with exact commit
            if dep_git not in lakefile_deps:
                validation_errors.append(
                    f"Dependency '{dep_git}' in math-dependencies.json not found in lakefile.toml [[require]] sections"
                )
                continue

            lakefile_rev = lakefile_deps[dep_git]

            # Check commit/rev matches exactly
            if lakefile_rev != dep_commit:
                validation_errors.append(
                    f"Dependency '{dep_git}': commit mismatch - "
                    f"math-dependencies.json has '{dep_commit}', lakefile.toml has '{lakefile_rev}'"
                )
                continue

            # All validations passed
            dependencies.append(
                public_model.ProjectInfo(
                    repo_url=dep_git,
                    commit=dep_commit,
                )
            )

    if validation_errors:
        error_msg = (
            f"Validation failed for {repo_url}@{commit}: {'; '.join(validation_errors)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    return dependencies



def main() -> int:
    """Main entry point for the dependency task."""
    logger.info("Dependency task starting")

    # Get task parameters from environment variables
    repo_url = os.getenv("URL")
    commit_hash = os.getenv("COMMIT_HASH")

    if repo_url is None or commit_hash is None:
        logger.error("Missing required environment variables: URL and COMMIT_HASH")
        return 1

    logger.info(f"Processing dependency task for {repo_url}@{commit_hash}")

    # Create temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Step 1: Clone repository
        if not clone_repository(repo_url, commit_hash, repo_path):
            logger.error("Failed to clone repository")
            return 1

        # Step 2: Parse and validate dependencies
        try:
            dependencies = parse_dependencies_from_repo(repo_path, repo_url, commit_hash)
            logger.info(f"Found and validated {len(dependencies)} dependencies")
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to parse dependencies: {e}")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error parsing dependencies: {e}", exc_info=True)
            return 1

        post_result = httpx.post(
            "http://dependency-service:8000/internal/projects",
            json=public_model.AddProjectInternalRequest(
                source=public_model.ProjectInfo(
                    repo_url=repo_url,
                    commit=commit_hash,
                ),
                dependencies=dependencies,
                is_valid=True,
            ).model_dump(),
        )

    if post_result.is_success:
        logger.info(f"Dependency task completed successfully and queued {len(dependencies)} dependencies.")
        return 0
    return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
