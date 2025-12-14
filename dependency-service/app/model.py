import typing
import common.model
from pydantic import BaseModel, Field


class HealthCheckResponse(common.model.HealthCheckResponse):
    service: typing.Literal["dependency-service"] = "dependency-service"


class AddProjectResponse(BaseModel):
    """Response from adding a project."""

    task_id: str = Field(..., description="Celery task ID for tracking")
    status: str = Field(..., description="Initial task status")


class ProjectInfo(BaseModel):
    """Information about a project in the database."""

    repo_url: str = Field(..., description="Repository URL")
    commit: str = Field(..., description="Commit hash")


class DependencyInfo(BaseModel):
    """Information about a dependency relationship."""

    source_repo: str = Field(..., description="Source project git URL")
    source_commit: str = Field(..., description="Source project commit hash")
    dependency_repo: str = Field(..., description="Dependency git URL")
    dependency_commit: str = Field(..., description="Dependency commit hash")


class AddDependencyResponse(BaseModel):
    """Response from adding a dependency."""

    success: bool
    message: str
