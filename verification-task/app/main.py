#!/usr/bin/env python3
"""
Verification Task - Dynamically spawned container to verify Lean 4 proofs.

This container:
1. Clones the Git repository at the specified commit
2. Runs Lean 4 verification
3. Outputs results and exits
"""

import os
import sys
import logging
import subprocess
import tempfile
from pathlib import Path
from common import logging_config

logging_config.configure_logging()

logger = logging.getLogger("verification-task")


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


def verify_lean_proof(work_dir: Path) -> tuple[bool, str]:
    """
    Verify a Lean 4 proof in the given directory.

    Returns:
        tuple: (success: bool, message: str)
    """
    logger.info("Starting Lean 4 verification")
    lake_build_result = subprocess.run(
        args=["lake", "build"],
        cwd=str(work_dir),
        capture_output=True,
        text=True,
        timeout=30 * SECONDS_PER_MINUTE,
    )

    combined_output = (
        "STDOUT:\n"
        f"{lake_build_result.stdout}\n"
        "\n"
        "STDERR:\n"
        f"{lake_build_result.stderr}"
    )

    if lake_build_result.returncode == 0:
        logger.info("Lean 4 verification succeeded")
        return True, combined_output
    else:
        logger.error(
            f"Lean 4 verification failed with exit code {lake_build_result.returncode}"
        )
        return False, combined_output


def main():
    """Main entry point for the verification task."""
    logger.info("Starting verification task")

    repo_url = os.environ.get("URL", "")
    commit_hash = os.environ.get("COMMIT_HASH", "")
    if not repo_url or not commit_hash:
        logger.error("URL and COMMIT_HASH environment variables must be set")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)

        # Clone repository
        if not clone_repository(repo_url, commit_hash, work_dir):
            logger.error("Failed to clone repository")
            sys.exit(1)

        # Verify Lean proof
        verification_success, verification_output = verify_lean_proof(work_dir)

        if verification_success:
            logger.info("Verification completed successfully")
            sys.exit(0)
        else:
            logger.error(f"Verification failed with output:\n{verification_output}")
            sys.exit(1)


if __name__ == "__main__":
    main()
