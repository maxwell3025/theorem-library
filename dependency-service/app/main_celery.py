from common.logging_config import configure_logging, configure_logging_celery
from common.config import config
import celery
import celery.utils.log
import docker

configure_logging()

celery_app = celery.Celery(
    "dependency_celery",
    broker="amqp://rabbitmq//",
    worker_prefetch_multiplier=1,
    broker_transport_options={"confirm_publish": True, "max_retries": 0},
)

configure_logging_celery(celery_app)

logger = celery.utils.log.get_task_logger("dependency_celery")

dependency_task_name = config.dependency_config.dependency_task_name

project_name = config.project_name


@celery_app.task(queue="dependency")
def clone_and_index_repository(repo_url: str, commit: str) -> dict:
    """Clone a repository at a specific commit and index its dependencies in Neo4j."""
    task_id = celery.current_task.request.id
    logger.info(f"Task {task_id}: Processing dependency task for {repo_url}@{commit}")

    if not task_id:
        logger.error("No task ID found for the current Celery task.")
        return {
            "status": "failed",
            "message": "No task ID found",
            "repo_url": repo_url,
            "commit": commit,
            "dependencies_count": 0,
        }

    client = docker.from_env()

    # Get the network name
    network_name = f"{project_name}_theorem-library"

    exit_code = -1
    container = None
    result = {
        "status": "failed",
        "message": "",
        "repo_url": repo_url,
        "commit": commit,
        "dependencies_count": 0,
    }

    try:
        # Run a new container instance of the dependency-task
        container = client.containers.run(
            image=f"{project_name}-{dependency_task_name}",
            network=network_name,
            name=f"dependency-task-{task_id}",
            detach=True,
            environment={
                "URL": repo_url,
                "COMMIT_HASH": commit,
            },
        )

        logger.info(f"Started dependency task container: {container.id}")

        # Wait for the container to complete
        wait_result = container.wait()
        exit_code = wait_result.get("StatusCode", -1)
        logger.info(f"Dependency task container completed with exit code: {exit_code}")

        logs = container.logs().decode("utf-8")
        logger.info(f"Dependency task logs:\n{logs}")

        if exit_code == 0:
            result = {
                "status": "success",
                "message": f"Successfully indexed {repo_url}@{commit}",
                "repo_url": repo_url,
                "commit": commit,
                "dependencies_count": 0,  # Could parse from logs if needed
            }
        else:
            result = {
                "status": "failed",
                "message": f"Dependency task failed with exit code {exit_code}",
                "repo_url": repo_url,
                "commit": commit,
                "dependencies_count": 0,
            }

    except Exception as e:
        logger.error(f"Error running dependency task: {e}", exc_info=True)
        result = {
            "status": "failed",
            "message": f"Error processing repository: {str(e)}",
            "repo_url": repo_url,
            "commit": commit,
            "dependencies_count": 0,
        }
    finally:
        if container:
            container.remove()
            logger.info(f"Removed dependency task container: {container.id}")

    return result
