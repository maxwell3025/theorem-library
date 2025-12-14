from common.logging_config import configure_logging, configure_logging_celery
from common.config import config
import celery
import celery.utils.log
import docker
import os

configure_logging()

celery_app = celery.Celery("dependency_celery", broker="amqp://rabbitmq//")

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
        neo4j_user = os.getenv("NEO4J_USER")
        if neo4j_user is None:
            raise ValueError("NEO4J_USER environment variable is not set")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if neo4j_password is None:
            raise ValueError("NEO4J_PASSWORD environment variable is not set")
        neo4j_host = config.neo4j.host
        neo4j_bolt_port = config.neo4j.bolt_port

        # Run a new container instance of the dependency-task
        container = client.containers.run(
            image=f"{project_name}-{dependency_task_name}",
            network=network_name,
            name=f"dependency-task-{task_id}",
            detach=True,
            environment={
                "URL": repo_url,
                "COMMIT_HASH": commit,
                "NEO4J_USER": neo4j_user,
                "NEO4J_PASSWORD": neo4j_password,
                "NEO4J_HOST": neo4j_host,
                "NEO4J_BOLT_PORT": neo4j_bolt_port,
            },
        )

        logger.info(f"Started dependency task container: {container.id}")

        # Wait for the container to complete
        wait_result = container.wait()
        exit_code = wait_result.get("StatusCode", -1)
        logger.info(
            f"Dependency task container completed with exit code: {exit_code}"
        )

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
