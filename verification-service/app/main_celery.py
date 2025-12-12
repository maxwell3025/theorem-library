from common.logging_config import configure_logging, configure_logging_celery
from common.config import config
import celery
import celery.utils.log
import docker

configure_logging()

celery_app = celery.Celery("main_celery", broker="amqp://rabbitmq//")

configure_logging_celery(celery_app)

logger = celery.utils.log.get_task_logger("main_celery")

verification_task_name = config.verification_config.verification_task_name

project_name = config.project_name


@celery_app.task
def process_verification_task(task_data: str) -> None:
    logger.info(f"Processing verification task with data: {task_data}")

    # Connect to Docker
    client = docker.from_env()

    # Get the network name
    network_name = f"{project_name}_theorem-library"

    try:
        # Run a new container instance of the verification-task
        container = client.containers.run(
            image=f"{project_name}-{verification_task_name}",
            network=network_name,
            name=f"verification-task-{celery.current_task.request.id}",
            detach=True,
            environment={"TASK_DATA": task_data},
        )

        logger.info(f"Started verification task container: {container.id}")

        # Wait for the container to complete
        result = container.wait()
        logger.info(f"Verification task container completed with status: {result}")

        # Get the logs from the container
        logs = container.logs().decode("utf-8")
        logger.info(f"Verification task logs: {logs}")

        container.remove()
        logger.info(f"Removed verification task container: {container.id}")

    except docker.errors.ImageNotFound:
        logger.error(
            f"Docker image not found: {project_name}-{verification_task_name}:latest"
        )
        raise
    except docker.errors.APIError as e:
        logger.error(f"Docker API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error running verification task: {e}")
        raise
