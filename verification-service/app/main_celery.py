from common.logging_config import configure_logging, configure_logging_celery
from common.config import config
import common.api.redis
import celery
import celery.utils.log
import docker
import httpx
import model
import os
from common.dependency_service import public_model

configure_logging()

celery_app = celery.Celery("main_celery", broker="amqp://rabbitmq//", worker_prefetch_multiplier=1)

configure_logging_celery(celery_app)

logger = celery.utils.log.get_task_logger("main_celery")

verification_task_name = config.verification_config.verification_task_name

project_name = config.project_name


@celery_app.task(queue="verification")
def process_verification_task(task_data_raw: str) -> None:
    logger.info(f"Processing verification task with data: {task_data_raw} on pid={os.getpid()}")

    task_data = model.VerificationRequest.model_validate_json(task_data_raw)
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
            # Run a new container instance of the verification-task
            container = client.containers.run(
                image=f"{project_name}-{verification_task_name}",
                network=network_name,
                name=f"verification-task-{task_id}",
                detach=True,
                environment={
                    "URL": task_data.repo_url,
                    "COMMIT_HASH": task_data.commit_hash,
                },
            )

            logger.info(f"Started verification task container: {container.id}")

            # Wait for the container to complete
            result = container.wait()
            logger.info(f"Result object from container wait: {result}")
            exit_code = result.get("StatusCode", -1)
            logger.info(
                f"Verification task container completed with exit code: {exit_code}"
            )

            if exit_code != 0:
                logs = container.logs().decode("utf-8")
                logger.info(f"Verification task logs:\n{logs}")

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
                        url="http://dependency-service:8000/internal/verification_status",
                        json=status_request.model_dump(),
                        timeout=30,
                    )
                    if status_result.is_success:
                        logger.info(
                            f"Updated verification status in dependency-service: {exit_code == 0}"
                        )
                    else:
                        logger.error(
                            f"Failed to update verification status: {status_result.status_code}\n"
                            f"{status_result.text[:500]}"
                        )
                except Exception as e:
                    logger.error(f"Exception while updating verification status: {e}")
            except Exception as e:
                logger.error(f"Failed to update Redis status: {e}")
            if container:
                container.remove()
                logger.info(f"Removed verification task container: {container.id}")
