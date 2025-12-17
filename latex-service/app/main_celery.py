from common.logging_config import configure_logging, configure_logging_celery
from common.config import config
import common.api.redis
import celery
import celery.utils.log
import docker
import httpx
import model
from common.dependency_service import public_model

configure_logging()

celery_app = celery.Celery("main_celery", broker="amqp://rabbitmq//")

configure_logging_celery(celery_app)

logger = celery.utils.log.get_task_logger("main_celery")

latex_task_name = config.latex_config.latex_task_name

project_name = config.project_name


@celery_app.task(queue="latex")
def process_latex_task(task_data_raw: str) -> None:
    logger.info(f"Processing LaTeX task with data: {task_data_raw}")

    # Validate task data with Pydantic
    task_data = model.LaTeXRequest.model_validate_json(task_data_raw)
    redis_key = task_data.redis_key()
    task_id = celery.current_task.request.id
    if not task_id:
        logger.error("No task ID found for the current Celery task.")
        return

    with common.api.redis.get_redis_client() as redis_client:
        # Validate and store status with task_id
        redis_data = model.RedisTaskData(status="running", task_id=task_id)
        redis_client.set(redis_key, redis_data.model_dump_json())
        redis_client.expire(redis_key, 86400)  # Expire after 24 hours

        client = docker.from_env()

        # Get the network name
        network_name = f"{project_name}_theorem-library"

        exit_code = -1
        container = None
        try:
            # Run a new container instance of the latex-task
            container = client.containers.run(
                image=f"{project_name}-{latex_task_name}",
                network=network_name,
                name=f"latex-task-{task_id}",
                detach=True,
                environment={
                    "URL": task_data.repo_url,
                    "COMMIT_HASH": task_data.commit_hash,
                },
            )

            logger.info(f"Started LaTeX task container: {container.id}")

            # Wait for the container to complete
            result = container.wait()
            logger.info(f"Result object from container wait: {result}")
            exit_code = result.get("StatusCode", -1)
            logger.info(f"LaTeX task container completed with exit code: {exit_code}")

            if exit_code != 0:
                logs = container.logs().decode("utf-8")
                logger.info(f"LaTeX task logs:\n{logs}")

        except Exception as e:
            exit_code = -1
        finally:
            try:
                # Validate and store final status with task_id
                final_status: model.TaskStatus = "success" if exit_code == 0 else "fail"
                redis_data = model.RedisTaskData(status=final_status, task_id=task_id)
                redis_client.set(redis_key, redis_data.model_dump_json())
                redis_client.expire(redis_key, 86400)  # Expire after 24 hours

                # Update status in dependency-service
                status_request = public_model.UpdateStatusRequest(
                    repo_url=task_data.repo_url,
                    commit=task_data.commit_hash,
                    has_valid_status=(exit_code == 0),
                )
                try:
                    status_result = httpx.post(
                        url="http://dependency-service:8000/internal/paper_status",
                        json=status_request.model_dump(),
                        timeout=30,
                    )
                    if status_result.is_success:
                        logger.info(
                            f"Updated paper status in dependency-service: {exit_code == 0}"
                        )
                    else:
                        logger.error(
                            f"Failed to update paper status: {status_result.status_code}\n"
                            f"{status_result.text[:500]}"
                        )
                except Exception as e:
                    logger.error(f"Exception while updating paper status: {e}")
            except Exception as e:
                logger.error(f"Failed to update Redis status: {e}")
            if container:
                container.remove()
                logger.info(f"Removed LaTeX task container: {container.id}")
