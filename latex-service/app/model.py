import typing
import common.model
from pydantic import BaseModel


TaskStatus = typing.Literal["queued", "running", "success", "fail"]


class HealthCheckResponse(common.model.HealthCheckResponse):
    service: typing.Literal["latex-service"] = "latex-service"


class LaTeXRequest(BaseModel):
    """Request to compile a LaTeX document."""

    repo_url: str
    commit_hash: str

    def redis_key(self) -> str:
        """Generate Redis key from repo_url and commit_hash."""
        return f"latex:{self.repo_url}:{self.commit_hash}"


class LaTeXTaskResponse(BaseModel):
    """Response when a LaTeX compilation task is queued."""

    repo_url: str
    commit_hash: str
    status: typing.Literal["queued"] = "queued"


class LaTeXStatus(BaseModel):
    """Valid LaTeX compilation status values."""

    status: TaskStatus


class RedisTaskData(BaseModel):
    """Data stored in Redis for each LaTeX compilation task."""

    status: TaskStatus
    task_id: str


class TaskStatusResponse(BaseModel):
    """Response with task status information."""

    repo_url: str
    commit_hash: str
    status: TaskStatus | typing.Literal["not_found"]
    task_id: str | None = None
