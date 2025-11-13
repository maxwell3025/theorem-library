import fastapi
import logging
import model
import common.model
import common.api.postgres
import typing
import os

logger = logging.Logger("latex-service")

app = fastapi.FastAPI()

PDF_SERVICE_BASE=os.getenv("PDF_SERVICE_BASE", default="http://pdf-service:8000")


@app.get("/health", response_model=model.HealthCheckResponse)
async def health_check() -> fastapi.Response:
    # Currently, nothing can cause a service to report itself as unhealthy
    status: common.model.HealthCheckStatus = "healthy"
    status_code = 200 if status == "healthy" else 503
    # Use methods defined in /common to run health checks
    dependencies: typing.Dict[str, common.model.HealthCheckDependency] = {
        "postgres": common.api.postgres.check_health(),
        "pdf-service": common.api.check_service_health(service_base=PDF_SERVICE_BASE)
    }

    response_content = model.HealthCheckResponse(
        status=status,
        dependencies=dependencies,
    )

    return fastapi.Response(
        content=response_content.model_dump_json(exclude_none=True),
        status_code=status_code,
    )
