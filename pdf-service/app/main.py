import fastapi
import logging
import model
import common.model
import common.middleware
from common.logging_config import configure_logging, configure_logging_uvicorn
import typing
import uvicorn
import hashlib
import base64
import binascii
import aiofiles
from pathlib import Path

configure_logging()

logger = logging.getLogger("pdf-service")

app = fastapi.FastAPI()

app.add_middleware(common.middleware.CorrelationIdMiddleware)

# Base directory for PDF storage
PDF_STORAGE_DIR = Path("/data/pdfs")
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_pdf_path(git_url: str, commit_hash: str) -> Path:
    """Generate a filesystem path for a PDF based on git_url and commit_hash.

    Uses SHA256 hash of git_url to create a directory, then stores by commit_hash.
    This avoids filesystem issues with special characters in URLs.
    """
    url_hash = hashlib.sha256(git_url.encode()).hexdigest()
    # Create nested directory structure: first 2 chars / next 2 chars / rest
    dir_path = PDF_STORAGE_DIR / url_hash[:2] / url_hash[2:4] / url_hash
    dir_path.mkdir(parents=True, exist_ok=True)

    # Store metadata file alongside PDFs
    metadata_file = dir_path / ".url"
    if not metadata_file.exists():
        with open(metadata_file, "w") as f:
            f.write(git_url)

    return dir_path / f"{commit_hash}.pdf"


@app.get("/health", response_model=model.HealthCheckResponse)
async def health_check() -> fastapi.Response:
    # Currently, nothing can cause a service to report itself as unhealtry
    status: common.model.HealthCheckStatus = "healthy"
    status_code = 200 if status == "healthy" else 503
    # Use methods defined in /common to run health checks
    dependencies: typing.Dict[str, common.model.HealthCheckDependency] = {}

    response_content = model.HealthCheckResponse(
        status=status,
        dependencies=dependencies,
    )

    return fastapi.Response(
        content=response_content.model_dump_json(exclude_none=True),
        status_code=status_code,
    )


@app.post("/pdf", response_model=model.PDFCreateResponse)
async def create_pdf(request: model.PDFCreateRequest) -> fastapi.Response:
    """Create a PDF file for a specific git repository and commit."""

    pdf_path = get_pdf_path(request.git_url, request.commit_hash)
    if pdf_path.exists():
        return fastapi.responses.JSONResponse(
            content={"error": "PDF already exists. Use PUT to update."},
            status_code=409,
        )

    try:
        pdf_bytes = base64.b64decode(request.pdf_data)
    except binascii.Error as e:
        logger.error(f"Invalid base64 data: {e}")
        return fastapi.responses.JSONResponse(
            content={"error": "Invalid base64-encoded PDF data"},
            status_code=400,
        )

    async with aiofiles.open(pdf_path, "wb") as f:
        await f.write(pdf_bytes)
    size_bytes = len(pdf_bytes)
    logger.info(
        f"Created PDF for {request.git_url}@{request.commit_hash}, size: {size_bytes} bytes"
    )

    return fastapi.responses.JSONResponse(
        content=model.PDFUpdateResponse(
            git_url=request.git_url,
            commit_hash=request.commit_hash,
            size_bytes=size_bytes,
        ).model_dump(),
        status_code=201,
    )


@app.get(
    "/{git_url_encoded}/{commit_hash}/main.pdf", response_model=model.PDFReadResponse
)
async def read_pdf(
    git_url_encoded: str = fastapi.Path(...),
    commit_hash: str = fastapi.Path(...),
) -> fastapi.Response:
    """Read a PDF file for a specific git repository and commit."""

    git_url = base64.urlsafe_b64decode(git_url_encoded.encode()).decode()

    logger.info(f"Reading PDF for {git_url}@{commit_hash}")
    pdf_path = get_pdf_path(git_url, commit_hash)

    if not pdf_path.exists():
        return fastapi.responses.JSONResponse(
            content={"error": "PDF not found"},
            status_code=404,
        )

    try:
        # Read file and encode as base64
        async with aiofiles.open(pdf_path, "rb") as f:
            pdf_bytes = await f.read()
        return fastapi.Response(
            media_type="application/pdf",
            content=pdf_bytes,
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Failed to read PDF: {e}")
        return fastapi.responses.JSONResponse(
            content={"error": f"Failed to read PDF: {str(e)}"},
            status_code=500,
        )


@app.put("/pdf", response_model=model.PDFUpdateResponse)
async def update_pdf(request: model.PDFUpdateRequest) -> fastapi.Response:
    """Update a PDF file for a specific git repository and commit."""

    pdf_path = get_pdf_path(request.git_url, request.commit_hash)

    resource_exists = pdf_path.exists()
    try:
        pdf_bytes = base64.b64decode(request.pdf_data)
    except binascii.Error as e:
        logger.error(f"Invalid base64 data: {e}")
        return fastapi.responses.JSONResponse(
            content={"error": "Invalid base64-encoded PDF data"},
            status_code=400,
        )

    async with aiofiles.open(pdf_path, "wb") as f:
        await f.write(pdf_bytes)
    size_bytes = len(pdf_bytes)
    logger.info(
        f"{'Updated' if resource_exists else 'Created'} PDF for {request.git_url}@{request.commit_hash}, size: {size_bytes} bytes"
    )

    return fastapi.responses.JSONResponse(
        content=model.PDFUpdateResponse(
            git_url=request.git_url,
            commit_hash=request.commit_hash,
            size_bytes=size_bytes,
        ).model_dump(),
        status_code=204 if resource_exists else 201,
    )


@app.delete("/pdf", response_model=model.PDFDeleteResponse)
async def delete_pdf(
    git_url: str = fastapi.Query(...),
    commit_hash: str = fastapi.Query(...),
) -> fastapi.Response:
    """Delete a PDF file for a specific git repository and commit."""

    pdf_path = get_pdf_path(git_url, commit_hash)

    if not pdf_path.exists():
        return fastapi.responses.JSONResponse(
            content={"error": "PDF not found"},
            status_code=404,
        )

    try:
        pdf_path.unlink()
        logger.info(f"Deleted PDF for {git_url}@{commit_hash}")

        response = model.PDFDeleteResponse(
            git_url=git_url,
            commit_hash=commit_hash,
        )

        return fastapi.responses.JSONResponse(
            content=response.model_dump(),
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Failed to delete PDF: {e}")
        return fastapi.responses.JSONResponse(
            content={"error": f"Failed to delete PDF: {str(e)}"},
            status_code=500,
        )


if __name__ == "__main__":
    # Get uvicorn's default logging config and customize it
    log_config = uvicorn.config.LOGGING_CONFIG
    configure_logging_uvicorn(log_config)

    # Start uvicorn with custom logging config
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
