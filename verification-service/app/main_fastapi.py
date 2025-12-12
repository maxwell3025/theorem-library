import fastapi
import logging
import model
import common.model
import common.api.postgres
import common.middleware
from common.logging_config import configure_logging, configure_logging_uvicorn
import typing
import main_celery
import uvicorn

configure_logging()

logger = logging.getLogger("verification-service")

app = fastapi.FastAPI()

app.add_middleware(common.middleware.CorrelationIdMiddleware)


@app.get("/health", response_model=model.HealthCheckResponse)
async def health_check(x_correlation_id: str = fastapi.Header()) -> fastapi.Response:
    # Currently, nothing can cause a service to report itself as unhealthy
    status: common.model.HealthCheckStatus = "healthy"
    status_code = 200 if status == "healthy" else 503
    # Use methods defined in /common to run health checks
    dependencies: typing.Dict[str, common.model.HealthCheckDependency] = {
        "postgres": common.api.postgres.check_health()
    }

    response_content = model.HealthCheckResponse(
        status=status,
        dependencies=dependencies,
    )

    return fastapi.Response(
        content=response_content.model_dump_json(exclude_none=True),
        status_code=status_code,
    )


@app.post("/run")
async def verify() -> fastapi.Response:
    task = main_celery.process_verification_task.delay("task data")
    return fastapi.responses.JSONResponse(
        content={"task_id": task.id, "status": "Queued"}, status_code=200
    )


if __name__ == "__main__":
    # Get uvicorn's default logging config and customize it
    log_config = uvicorn.config.LOGGING_CONFIG
    configure_logging_uvicorn(log_config)
    
    # Start uvicorn with custom logging config
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
