"""
Git HTTP server for testing.

This server provides HTTP access to test git repositories, allowing
the test suite to clone repositories using git:// or http:// protocols.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse, PlainTextResponse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
)
logger = logging.getLogger("git-server")

app = FastAPI(title="Git Test Server")

# Base directory for git repositories
GIT_REPOS_BASE = Path("/git-repos")

# Store commit hashes for each repository (populated on startup)
REPO_COMMITS = {}


def get_repo_path(repo_name: str) -> Optional[Path]:
    """Get the full path to a repository, validating it exists."""
    repo_path = GIT_REPOS_BASE / repo_name
    if not repo_path.exists() or not (repo_path / ".git").exists():
        return None
    return repo_path


def get_repo_head_commit(repo_path: Path) -> str:
    """Get the HEAD commit hash for a repository."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get HEAD commit: {result.stderr}")
    return result.stdout.strip()


@app.on_event("startup")
async def populate_commits():
    """Populate the REPO_COMMITS dictionary on startup."""
    logger.info("Populating repository commit information...")
    for repo_dir in GIT_REPOS_BASE.iterdir():
        if repo_dir.is_dir() and (repo_dir / ".git").exists():
            repo_name = repo_dir.name
            try:
                commit = get_repo_head_commit(repo_dir)
                REPO_COMMITS[repo_name] = commit
                logger.info(f"Repository {repo_name}: commit {commit}")
            except Exception as e:
                logger.error(f"Failed to get commit for {repo_name}: {e}")
    logger.info(f"Loaded {len(REPO_COMMITS)} repositories")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "repositories": len(REPO_COMMITS)}


@app.get("/repositories")
async def list_repositories():
    """List all available repositories with their commit hashes."""
    return {
        "repositories": [
            {
                "name": name,
                "url": f"http://git-server:8000/{name}",
                "commit": commit,
            }
            for name, commit in REPO_COMMITS.items()
        ]
    }


@app.get("/{repo_name}/info/refs")
async def git_info_refs(repo_name: str, service: Optional[str] = None):
    """Handle git info/refs requests for git clone operations."""
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        raise HTTPException(status_code=404, detail=f"Repository {repo_name} not found")

    if service:
        # Smart HTTP protocol
        logger.info(f"Git smart protocol request for {repo_name}: {service}")

        result = subprocess.run(
            [
                "git",
                service.replace("git-", ""),
                "--stateless-rpc",
                "--advertise-refs",
                str(repo_path),
            ],
            capture_output=True,
        )

        if result.returncode != 0:
            logger.error(f"Git command failed: {result.stderr!r}")
            raise HTTPException(status_code=500, detail="Git command failed")

        # Return with proper content type for smart protocol
        content_type = f"application/x-{service}-advertisement"
        response_data = f"001e# service={service}\n0000".encode() + result.stdout

        return Response(
            content=response_data,
            media_type=content_type,
        )
    else:
        # Dumb HTTP protocol - serve the refs file
        logger.info(f"Git dumb protocol request for {repo_name}/info/refs")
        result = subprocess.run(
            ["git", "update-server-info"],
            cwd=repo_path,
            capture_output=True,
        )

        refs_file = repo_path / ".git" / "info" / "refs"
        if refs_file.exists():
            with open(refs_file, "rb") as f:
                return Response(content=f.read(), media_type="text/plain")
        else:
            raise HTTPException(status_code=404, detail="refs file not found")


@app.post("/{repo_name}/git-upload-pack")
async def git_upload_pack(repo_name: str, body: bytes | None = None):
    """Handle git-upload-pack requests for fetching/cloning."""
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        raise HTTPException(status_code=404, detail=f"Repository {repo_name} not found")

    logger.info(f"Git upload-pack request for {repo_name}")

    # Run git-upload-pack
    process = subprocess.Popen(
        ["git", "upload-pack", "--stateless-rpc", str(repo_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate(input=body if body else b"")

    if process.returncode != 0:
        logger.error(f"Git upload-pack failed: {stderr.decode()}")
        raise HTTPException(status_code=500, detail="Git upload-pack failed")

    return Response(
        content=stdout,
        media_type="application/x-git-upload-pack-result",
    )


@app.get("/{repo_name}/HEAD")
async def get_head(repo_name: str):
    """Serve the HEAD file for dumb HTTP protocol."""
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        raise HTTPException(status_code=404, detail=f"Repository {repo_name} not found")

    head_file = repo_path / ".git" / "HEAD"
    if head_file.exists():
        with open(head_file, "r") as f:
            return PlainTextResponse(content=f.read())
    raise HTTPException(status_code=404, detail="HEAD file not found")


@app.get("/{repo_name}/objects/{path:path}")
async def get_object(repo_name: str, path: str):
    """Serve git objects for dumb HTTP protocol."""
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        raise HTTPException(status_code=404, detail=f"Repository {repo_name} not found")

    object_file = repo_path / ".git" / "objects" / path
    if object_file.exists() and object_file.is_file():
        with open(object_file, "rb") as f:
            return Response(content=f.read(), media_type="application/octet-stream")
    raise HTTPException(status_code=404, detail="Object not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
