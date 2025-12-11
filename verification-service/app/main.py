import fastapi
import logging
import model
import common.model
import common.api.postgres
import common.middleware
import common.logging_config
import typing
import celery
import docker
import os

logger = logging.Logger("verification-service")

app = fastapi.FastAPI()

celery_app = celery.Celery("verification-service", broker="amqp://rabbitmq//")

app.add_middleware(common.middleware.CorrelationIdMiddleware)


@app.get("/health", response_model=model.HealthCheckResponse)
async def health_check(x_correlation_id: str = fastapi.Header()) -> fastapi.Response:
    logger.info(f"[{x_correlation_id}] Received healthcheck request")
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
    task = process_verification_task.delay("task data")
    return fastapi.responses.JSONResponse(
        content={"task_id": task.id, "status": "Queued"}, status_code=200
    )


@celery_app.task
def process_verification_task(task_data: str) -> None:
    logger.info(f"Processing verification task with data: {task_data}")

    # Connect to Docker
    client = docker.from_env()

    # Get the verification task image tag from environment variable
    verification_task_tag = os.getenv(
        "VERIFICATION_TASK_TAG", "verification-task:latest"
    )

    # Get the network name
    network_name = "theorem-library"

    try:
        # Run a new container instance of the verification-task
        container = client.containers.run(
            image=verification_task_tag,
            network=network_name,
            detach=True,
            remove=True,  # Auto-remove container when it exits
            environment={"TASK_DATA": task_data},
        )

        logger.info(f"Started verification task container: {container.id}")

        # Wait for the container to complete
        result = container.wait()
        logger.info(f"Verification task container completed with status: {result}")

        # Get the logs from the container
        logs = container.logs().decode("utf-8")
        logger.info(f"Verification task logs: {logs}")

    except docker.errors.ImageNotFound:
        logger.error(f"Docker image not found: {verification_task_tag}")
        raise
    except docker.errors.APIError as e:
        logger.error(f"Docker API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error running verification task: {e}")
        raise
