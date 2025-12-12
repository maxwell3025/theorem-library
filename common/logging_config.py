import logging
import typing

if typing.TYPE_CHECKING:
    import celery

LOGGING_FORMAT = "[%(asctime)s.%(msecs)03d][%(name)-20s][%(levelname)s] %(message)s"
LOGGING_FORMAT_CELERY = "[%(asctime)s][%(name)-20s][%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=LOGGING_FORMAT,
        datefmt=DATE_FORMAT,
    )


def configure_logging_uvicorn(logging_config: dict) -> None:
    """
    Configure logging for a Uvicorn application using dependency injection.

    Args:
        logging_config: The Uvicorn LOGGING_CONFIG dictionary
    """
    # Update the log format for the 'uvicorn.access' handler
    logging_config["formatters"]["access"]["fmt"] = LOGGING_FORMAT
    logging_config["formatters"]["access"]["datefmt"] = DATE_FORMAT

    # You can also change the format for the 'default' handler
    logging_config["formatters"]["default"]["fmt"] = LOGGING_FORMAT
    logging_config["formatters"]["default"]["datefmt"] = DATE_FORMAT


def configure_logging_celery(celery_app: "celery.Celery") -> None:
    """
    Configure logging for a Celery application using dependency injection.

    Args:
        celery_app: The Celery application instance
    """
    # Set Celery's logger level to INFO
    logging.getLogger("celery").setLevel(logging.INFO)

    # Configure Celery to use our custom logging format
    celery_app.conf.update(
        worker_log_format=LOGGING_FORMAT_CELERY,
        worker_task_log_format=LOGGING_FORMAT_CELERY,
    )
