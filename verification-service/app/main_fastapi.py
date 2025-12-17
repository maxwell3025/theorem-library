import fastapi
import logging
import model
import common.model
import common.api
import common.api.redis
import common.middleware
from common.logging_config import configure_logging, configure_logging_uvicorn
import typing
import main_celery
import uvicorn

configure_logging()

logger = logging.getLogger("verification-service")

app = fastapi.FastAPI()

app.add_middleware(common.middleware.CorrelationIdMiddleware)

SECONDS_PER_DAY = 86400


@app.get("/health", response_model=model.HealthCheckResponse)
async def health_check(x_correlation_id: str = fastapi.Header()) -> fastapi.Response:
    # Currently, nothing can cause a service to report itself as unhealthy
    status: common.model.HealthCheckStatus = "healthy"
    status_code = 200 if status == "healthy" else 503
    # Use methods defined in /common to run health checks
    dependencies: typing.Dict[str, common.model.HealthCheckDependency] = {
        "redis": common.api.redis.check_health(),
    }

    response_content = model.HealthCheckResponse(
        status=status,
        dependencies=dependencies,
    )

    return fastapi.responses.JSONResponse(
        content=response_content.model_dump(exclude_none=True),
        status_code=status_code,
    )


@app.post("/run", response_model=model.VerificationTaskResponse)
async def verify(
    request: model.VerificationRequest,
) -> fastapi.Response:

    try:
        task = main_celery.process_verification_task.delay(request.model_dump_json())
    except Exception as e:
        logger.error(f"Failed to queue verification task: {e}")
        return fastapi.responses.JSONResponse(
            content={
                "error": "Failed to queue task",
                "message": str(e),
                "reason": "Task queue may be full or unavailable",
            },
            status_code=503,
        )

    with common.api.redis.get_redis_client() as redis_client:
        redis_key = request.redis_key()
        redis_data = model.RedisTaskData(
            status="queued",
            task_id=task.id,
        )
        redis_client.set(redis_key, redis_data.model_dump_json())
        redis_client.expire(redis_key, SECONDS_PER_DAY)

    return fastapi.responses.JSONResponse(
        content=model.VerificationTaskResponse(
            repo_url=request.repo_url,
            commit_hash=request.commit_hash,
            status="queued",
            task_id=task.id,
        ).model_dump(),
        status_code=202,
    )


@app.get("/status")
async def get_status(request: model.VerificationRequest) -> fastapi.Response:
    redis_key = request.redis_key()

    redis_data: model.RedisTaskData | None = None
    with common.api.redis.get_redis_client() as redis_client:
        redis_value = redis_client.get(redis_key)
        if redis_value:
            try:
                redis_data = model.RedisTaskData.model_validate_json(redis_value)
            except Exception:
                logger.error(f"Invalid data in Redis: {redis_value}")
                redis_client.delete(redis_key)

    if redis_data is not None:
        return fastapi.responses.JSONResponse(
            content=model.TaskStatusResponse(
                repo_url=request.repo_url,
                commit_hash=request.commit_hash,
                status=redis_data.status,
                task_id=redis_data.task_id,
            ).model_dump(),
            status_code=200,
        )
    else:
        return fastapi.responses.JSONResponse(
            content={
                "repo_url": request.repo_url,
                "commit_hash": request.commit_hash,
                "status": "not_found",
            },
            status_code=404,
        )


if __name__ == "__main__":
    # Get uvicorn's default logging config and customize it
    log_config = uvicorn.config.LOGGING_CONFIG
    configure_logging_uvicorn(log_config)

    # Start uvicorn with custom logging config
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
