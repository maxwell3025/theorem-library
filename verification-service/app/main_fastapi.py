import fastapi
import logging
import model
import common.model
import common.api.postgres
import common.api.redis
import common.middleware
from common.logging_config import configure_logging, configure_logging_uvicorn
import typing
import main_celery
import uvicorn
import time
import json

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
        "redis": common.api.redis.check_health(),
    }

    response_content = model.HealthCheckResponse(
        status=status,
        dependencies=dependencies,
    )

    return fastapi.Response(
        content=response_content.model_dump_json(exclude_none=True),
        status_code=status_code,
    )


@app.post("/run", response_model=model.VerificationTaskResponse)
async def verify(
    request: model.VerificationRequest,
) -> fastapi.Response:
    # Validate request with Pydantic
    validated_request = model.VerificationRequest.model_validate(request)

    redis_key = validated_request.redis_key()
    task_data = validated_request.model_dump_json()

    # Queue the task first to get task_id
    task = main_celery.process_verification_task.delay(task_data)

    # Store initial status in Redis
    redis_client = common.api.redis.get_redis_client()
    try:
        # Validate and store status with task_id
        redis_data = model.RedisTaskData(status="queued", task_id=task.id)
        redis_client.set(redis_key, redis_data.model_dump_json())
        redis_client.expire(redis_key, 86400)  # Expire after 24 hours
    except Exception as e:
        logger.error(f"Failed to store task status in Redis: {e}")
        redis_client.close()
        return fastapi.responses.JSONResponse(
            content={"error": "Failed to queue task"}, status_code=500
        )
    finally:
        redis_client.close()

    return fastapi.responses.JSONResponse(
        content={
            "repo_url": validated_request.repo_url,
            "commit_hash": validated_request.commit_hash,
            "status": "queued",
        },
        status_code=202,
    )


@app.post("/status")
async def get_status(request: model.VerificationRequest) -> fastapi.Response:
    try:
        validated_request = model.VerificationRequest.model_validate(request)
    except Exception as e:
        return fastapi.responses.JSONResponse(
            content={"error": f"Invalid request parameters: {e}"}, status_code=400
        )

    redis_key = validated_request.redis_key()

    response = None

    with common.api.redis.get_redis_client() as redis_client:
        status: model.TaskStatus | typing.Literal["not_found"] = "not_found"
        task_id = None

        redis_value = redis_client.get(redis_key)
        if redis_value:
            try:
                redis_data = model.RedisTaskData.model_validate_json(redis_value)
                status = redis_data.status
                task_id = redis_data.task_id
            except Exception:
                logger.error(f"Invalid data in Redis: {redis_value}")

        response = model.TaskStatusResponse(
            repo_url=validated_request.repo_url,
            commit_hash=validated_request.commit_hash,
            status=status,
            task_id=task_id,
        )

    if response is None:
        return fastapi.responses.JSONResponse(
            content={"error": "Failed to retrieve task status"}, status_code=500
        )
    return fastapi.responses.JSONResponse(
        content=response.model_dump(), status_code=200
    )


if __name__ == "__main__":
    # Get uvicorn's default logging config and customize it
    log_config = uvicorn.config.LOGGING_CONFIG
    configure_logging_uvicorn(log_config)

    # Start uvicorn with custom logging config
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
