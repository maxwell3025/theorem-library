import typing
import common.model
from pydantic import BaseModel, Field


class HealthCheckResponse(common.model.HealthCheckResponse):
    service: typing.Literal["pdf-service"] = "pdf-service"


class PDFIdentifier(BaseModel):
    """Identifier for a PDF document based on git repository and commit."""

    git_url: str = Field(..., description="Git repository URL")
    commit_hash: str = Field(..., description="Commit hash")


class PDFCreateRequest(BaseModel):
    """Request to create a PDF document."""

    git_url: str = Field(..., description="Git repository URL")
    commit_hash: str = Field(..., description="Commit hash")
    pdf_data: str = Field(..., description="Base64-encoded PDF content")


class PDFCreateResponse(BaseModel):
    """Response after creating a PDF."""

    git_url: str
    commit_hash: str
    size_bytes: int


class PDFReadResponse(BaseModel):
    """Response when reading a PDF."""

    git_url: str
    commit_hash: str
    pdf_data: str = Field(..., description="Base64-encoded PDF content")
    size_bytes: int


class PDFUpdateRequest(BaseModel):
    """Request to update a PDF document."""

    git_url: str = Field(..., description="Git repository URL")
    commit_hash: str = Field(..., description="Commit hash")
    pdf_data: str = Field(..., description="Base64-encoded PDF content")


class PDFUpdateResponse(BaseModel):
    """Response after updating a PDF."""

    git_url: str
    commit_hash: str
    size_bytes: int


class PDFDeleteResponse(BaseModel):
    """Response after deleting a PDF."""

    git_url: str
    commit_hash: str
