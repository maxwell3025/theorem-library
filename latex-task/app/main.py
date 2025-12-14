#!/usr/bin/env python3
"""
LaTeX Task - Dynamically spawned container to compile LaTeX documents.

This container:
1. Receives task data via URL and COMMIT_HASH environment variables
2. Clones the Git repository at the specified commit
3. Runs LaTeX compilation
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

logger = logging.getLogger("latex-task")


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


def compile_latex(work_dir: Path) -> tuple[bool, str]:
    """
    Compile a LaTeX document in the given directory.

    Looks for latex-source/main.tex and compiles it with pdflatex.

    Returns:
        tuple: (success: bool, message: str)
    """
    logger.info("Starting LaTeX compilation")

    # Check if latex-source/main.tex exists
    latex_dir = work_dir / "latex-source"
    main_tex = latex_dir / "main.tex"
    
    if not latex_dir.exists():
        msg = "latex-source directory not found in repository"
        logger.error(msg)
        return False, msg
    
    if not main_tex.exists():
        msg = "main.tex not found in latex-source directory"
        logger.error(msg)
        return False, msg

    # Run pdflatex to compile the LaTeX document
    # Run it twice to resolve references
    logger.info("Running 'pdflatex main.tex' (first pass)...")
    exit_code1, stdout1, stderr1 = run_command(
        ["pdflatex", "-interaction=nonstopmode", "main.tex"],
        cwd=str(latex_dir),
        timeout=600,  # 10 minutes timeout for large documents
    )

    logger.info("Running 'pdflatex main.tex' (second pass)...")
    exit_code2, stdout2, stderr2 = run_command(
        ["pdflatex", "-interaction=nonstopmode", "main.tex"],
        cwd=str(latex_dir),
        timeout=600,
    )

    combined_output = f"First pass:\nSTDOUT:\n{stdout1}\n\nSTDERR:\n{stderr1}\n\n"
    combined_output += f"Second pass:\nSTDOUT:\n{stdout2}\n\nSTDERR:\n{stderr2}"

    # Check if PDF was generated
    pdf_file = latex_dir / "main.pdf"
    if pdf_file.exists() and exit_code2 == 0:
        logger.info("LaTeX compilation succeeded")
        return True, combined_output
    else:
        logger.error(f"LaTeX compilation failed with exit code {exit_code2}")
        return False, combined_output


def main():
    """Main entry point for the LaTeX compilation task."""
    logger.info("Starting LaTeX compilation task")

    # Get task data from environment variables
    repo_url = os.environ.get("URL", "")
    commit_hash = os.environ.get("COMMIT_HASH", "")

    if not repo_url or not commit_hash:
        logger.error("URL and COMMIT_HASH environment variables must be set")
        sys.exit(1)

    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir) / "repo"
        work_dir.mkdir(parents=True, exist_ok=True)

        # Clone repository
        if not clone_repository(repo_url, commit_hash, work_dir):
            logger.error("Failed to clone repository")
            sys.exit(1)

        # Compile LaTeX document
        compilation_success, compilation_output = compile_latex(work_dir)

        # Log compilation output
        logger.info(f"Compilation output:\n{compilation_output}")

        if compilation_success:
            logger.info("LaTeX compilation completed successfully")
            sys.exit(0)
        else:
            logger.error("LaTeX compilation failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
