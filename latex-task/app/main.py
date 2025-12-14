#!/usr/bin/env python3
"""
LaTeX Task - Dynamically spawned container to compile LaTeX documents.

This container:
1. Receives task data via URL and COMMIT_HASH environment variables
2. Clones the Git repository at the specified commit
3. Runs LaTeX compilation
4. Outputs results and exits
"""

import base64
import os
import sys
import logging
import subprocess
import tempfile
import httpx
from pathlib import Path
from common import logging_config

logging_config.configure_logging()

logger = logging.getLogger("latex-task")


SECONDS_PER_MINUTE = 60

def clone_repository(repo_url: str, commit_hash: str, work_dir: Path) -> bool:
    """Clone a Git repository at a specific commit."""
    logger.info(f"Cloning repository {repo_url} at commit {commit_hash}")

    # Clone the repository
    clone_result = subprocess.run(
        args=["git", "clone", repo_url, str(work_dir)],
        capture_output=True,
        text=True,
        timeout=10*SECONDS_PER_MINUTE,
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
        timeout=10*SECONDS_PER_MINUTE,
    )

    logger.debug(f"Git checkout stdout: \n{checkout_result.stdout}")
    logger.debug(f"Git checkout stderr: \n{checkout_result.stderr}")

    if checkout_result.returncode != 0:
        logger.error(f"Failed to checkout commit {commit_hash}:\n{checkout_result.stderr}")
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

    latex_dir = work_dir / "latex-source"
    
    if not latex_dir.exists():
        msg = "latex-source directory not found in repository"
        logger.error(msg)
        return False, msg

    logger.info("Running 'pdflatex main.tex' (first pass)...")
    pdflatex_result1 = subprocess.run(
        args=["pdflatex", "-interaction=nonstopmode", "main.tex"],
        cwd=str(latex_dir),
        capture_output=True,
        text=True,
        timeout=10*SECONDS_PER_MINUTE,
    )

    # Run it twice to resolve references
    logger.info("Running 'pdflatex main.tex' (second pass)...")
    pdflatex_result2 = subprocess.run(
        args=["pdflatex", "-interaction=nonstopmode", "main.tex"],
        cwd=str(latex_dir),
        capture_output=True,
        text=True,
        timeout=10*SECONDS_PER_MINUTE,
    )

    combined_output = ( "First pass:\n"
                        "STDOUT:\n"
                       f"{pdflatex_result1.stdout}\n"
                        "\n"
                        "STDERR:\n"
                       f"{pdflatex_result1.stderr}\n"
                        "\n")
    combined_output += ( "Second pass:\n"
                         "STDOUT:\n"
                        f"{pdflatex_result2.stdout}\n"
                         "\n"
                         "STDERR:\n"
                        f"{pdflatex_result2.stderr}\n"
                         "\n")

    # Check if PDF was generated
    pdf_file = latex_dir / "main.pdf"
    if pdf_file.exists() and pdflatex_result2.returncode == 0:
        logger.info("LaTeX compilation succeeded")
        return True, combined_output
    else:
        logger.error(f"LaTeX compilation failed with exit code {pdflatex_result2.returncode}")
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
        work_dir = Path(temp_dir)

        if not clone_repository(repo_url, commit_hash, work_dir):
            logger.error("Failed to clone repository")
            sys.exit(1)

        compilation_success, compilation_output = compile_latex(work_dir)

        logger.info(f"Compilation output:\n{compilation_output}")
        if not compilation_success:
            logger.error("LaTeX compilation failed")
            sys.exit(1)
        
        with open(work_dir / "latex-source" / "main.pdf", "rb") as pdf_file:
            upload_result = httpx.put(
                url="http://pdf-service:8000/pdf",
                json={
                    "repo_url": repo_url,
                    "commit_hash": commit_hash,
                    "pdf-data": base64.b64encode(pdf_file.read()).decode('utf-8'),
                },
                timeout=30,
            )
            if upload_result.status_code == 201:
                logger.info("LaTeX compilation completed successfully")
                sys.exit(0)
            else:
                logger.error("Uploading PDF to pdf-service failed")
                sys.exit(1)


if __name__ == "__main__":
    main()
