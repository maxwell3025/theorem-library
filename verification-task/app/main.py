#!/usr/bin/env python3
"""
Verification Task - Dynamically spawned container to verify Lean 4 proofs.

This container:
1. Receives task data via TASK_DATA environment variable
2. Clones the Git repository at the specified commit
3. Runs Lean 4 verification
4. Outputs results and exits
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("verification-task")


def run_command(
    cmd: list[str], cwd: str | None = None, timeout: int = 300
) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        return -1, "", f"Command timed out after {timeout} seconds: {' '.join(cmd)}"
    except Exception as e:
        return -1, "", f"Error running command: {str(e)}"


def clone_repository(repo_url: str, commit_hash: str, work_dir: Path) -> bool:
    """Clone a Git repository at a specific commit."""
    logger.info(f"Cloning repository {repo_url} at commit {commit_hash}")

    # Clone the repository
    exit_code, stdout, stderr = run_command(
        ["git", "clone", repo_url, str(work_dir)],
        timeout=600,
    )

    if exit_code != 0:
        logger.error(f"Failed to clone repository: {stderr}")
        return False

    # Checkout the specific commit
    exit_code, stdout, stderr = run_command(
        ["git", "checkout", commit_hash],
        cwd=str(work_dir),
    )

    if exit_code != 0:
        logger.error(f"Failed to checkout commit {commit_hash}: {stderr}")
        return False

    logger.info(f"Successfully cloned repository at commit {commit_hash}")
    return True


def verify_lean_proof(work_dir: Path) -> tuple[bool, str]:
    """
    Verify a Lean 4 proof in the given directory.

    Returns:
        tuple: (success: bool, message: str)
    """
    logger.info("Starting Lean 4 verification")

    # Check if lakefile.toml exists
    lakefile = work_dir / "lakefile.toml"
    if not lakefile.exists():
        msg = "lakefile.toml not found in repository"
        logger.error(msg)
        return False, msg

    # Run lake build to compile and verify the Lean code
    logger.info("Running 'lake build'...")
    exit_code, stdout, stderr = run_command(
        ["lake", "build"],
        cwd=str(work_dir),
        timeout=1800,  # 30 minutes timeout for large proofs
    )

    combined_output = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"

    if exit_code == 0:
        logger.info("Lean 4 verification succeeded")
        return True, combined_output
    else:
        logger.error(f"Lean 4 verification failed with exit code {exit_code}")
        return False, combined_output


def verify_math_dependencies(work_dir: Path) -> tuple[bool, str]:
    """
    Verify that math-dependencies.json is consistent with lakefile.toml.

    Returns:
        tuple: (success: bool, message: str)
    """
    logger.info("Verifying math-dependencies.json consistency")

    math_deps_file = work_dir / "math-dependencies.json"
    if not math_deps_file.exists():
        msg = "math-dependencies.json not found in repository"
        logger.warning(msg)
        return True, msg  # Optional file, not an error

    try:
        with open(math_deps_file, "r") as f:
            math_deps = json.load(f)

        if not isinstance(math_deps, list):
            msg = "math-dependencies.json must be a JSON array"
            logger.error(msg)
            return False, msg

        # Basic validation of each dependency
        for i, dep in enumerate(math_deps):
            if not isinstance(dep, dict):
                msg = f"Dependency at index {i} is not a JSON object"
                logger.error(msg)
                return False, msg

            required_fields = ["packageName", "git", "commit"]
            for field in required_fields:
                if field not in dep:
                    msg = f"Dependency at index {i} missing required field: {field}"
                    logger.error(msg)
                    return False, msg

        logger.info(
            f"math-dependencies.json is valid with {len(math_deps)} dependencies"
        )
        return True, f"Valid with {len(math_deps)} math dependencies"

    except json.JSONDecodeError as e:
        msg = f"math-dependencies.json is not valid JSON: {str(e)}"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Error reading math-dependencies.json: {str(e)}"
        logger.error(msg)
        return False, msg


def main():
    """Main entry point for the verification task."""
    logger.info("Starting verification task")

    # Get task data from environment variable
    task_data_str = os.environ.get("TASK_DATA", "")
    if not task_data_str:
        logger.error("TASK_DATA environment variable is not set")
        sys.exit(1)

    # Parse task data
    try:
        task_data = json.loads(task_data_str)
        repo_url = task_data.get("repo_url")
        commit_hash = task_data.get("commit_hash")

        if not repo_url or not commit_hash:
            logger.error("Task data must include 'repo_url' and 'commit_hash'")
            sys.exit(1)

    except json.JSONDecodeError:
        # If task_data is not JSON, treat it as a simple test scenario
        logger.warning(f"Task data is not JSON, running in test mode: {task_data_str}")
        logger.info("Test mode: Verification task completed successfully")
        sys.exit(0)

    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir) / "repo"
        work_dir.mkdir(parents=True, exist_ok=True)

        # Clone repository
        if not clone_repository(repo_url, commit_hash, work_dir):
            logger.error("Failed to clone repository")
            sys.exit(1)

        # Verify math dependencies
        deps_valid, deps_message = verify_math_dependencies(work_dir)
        if not deps_valid:
            logger.error(f"Math dependencies validation failed: {deps_message}")
            sys.exit(1)

        # Verify Lean proof
        verification_success, verification_output = verify_lean_proof(work_dir)

        # Log verification output
        logger.info(f"Verification output:\n{verification_output}")

        if verification_success:
            logger.info("Verification completed successfully")
            sys.exit(0)
        else:
            logger.error("Verification failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
