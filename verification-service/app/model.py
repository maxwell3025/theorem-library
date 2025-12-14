import typing
import common.model
from pydantic import BaseModel


TaskStatus = typing.Literal["queued", "running", "success", "fail"]


class HealthCheckResponse(common.model.HealthCheckResponse):
    service: typing.Literal["verification-service"] = "verification-service"


class VerificationRequest(BaseModel):
    """Request to verify a Lean 4 proof."""

    repo_url: str
    commit_hash: str

    def redis_key(self) -> str:
        """Generate Redis key from repo_url and commit_hash."""
        return f"verification:{self.repo_url}:{self.commit_hash}"


class VerificationTaskResponse(BaseModel):
    """Response when a verification task is queued."""

    repo_url: str
    commit_hash: str
    status: typing.Literal["queued"] = "queued"
    task_id: str


class VerificationStatus(BaseModel):
    """Valid verification status values."""

    status: TaskStatus


class RedisTaskData(BaseModel):
    """Data stored in Redis for each verification task."""

    status: TaskStatus
    task_id: str


class TaskStatusResponse(BaseModel):
    """Response with task status information."""

    repo_url: str
    commit_hash: str
    status: TaskStatus | typing.Literal["not_found"]
    task_id: typing.Optional[str] = None
