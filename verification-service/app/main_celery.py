import logging
from common.logging_config import configure_logging
import celery
import celery.utils.log
import docker
import os

configure_logging()

logger = celery.utils.log.get_task_logger("verification-worker")

celery_app = celery.Celery("verification-worker", broker="amqp://rabbitmq//")

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
    network_name = "theorem-library_theorem-library"

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
