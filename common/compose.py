from typing import Dict, Optional, Union, List
from compose_pydantic import (  # type: ignore[import-untyped]
    ComposeSpecification,
    Service,
    BuildItem,
    Healthcheck,
    Condition,
)
from compose_pydantic.models import ListOfStrings  # type: ignore[import-untyped]

from common.config import config


class BuildItemModernized(BuildItem):
    """Build item with modernized field names."""

    additional_contexts: Optional[list[str]] = None


class ServiceModernized(Service):
    """Service with modernized field names."""

    build: Optional[BuildItemModernized] = None


class HealthcheckWithDefaults(Healthcheck):
    """Base Docker healthcheck configuration."""

    test: Union[str, List[str]] = ["CMD", "httpx", "http://localhost:8000/health"]
    interval: str = "1s"
    retries: float = 10
    timeout: str = "1s"
    start_period: str = "1s"


class ServiceWithDefaults(ServiceModernized):
    """Service with default values."""

    restart: str = "unless-stopped"
    networks: ListOfStrings = ListOfStrings(["theorem-library"])
    healthcheck: Optional[Healthcheck] = HealthcheckWithDefaults()


class BuildItemWithDefaults(BuildItemModernized):
    """Build item with default values."""

    additional_contexts: Optional[List[str]] = ["common=./common"]
    dockerfile: str = "Dockerfile"


class DockerComposeConfig(ComposeSpecification):
    """Docker Compose configuration using compose-pydantic."""

    name: str = config.project_name
    services: Dict[str, ServiceModernized] = {
        "postgres": ServiceWithDefaults(
            image="postgres:18",
            container_name="postgres",
            volumes=["pgdata:/var/lib/postgresql"],
            ports=["8000:${POSTGRES_PORT}"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
                f"POSTGRES_DB={config.postgres.database}",
            ],
            command=[
                "postgres",
                "-c",
                "log_destination=stderr",
                "-c",
                "logging_collector=off",
                "-c",
                "log_line_prefix='[%m][postgres            ][%e]'",
                "-c",
                "log_timezone=UTC",
            ],
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "pg_isready", "-U", "postgres"],
            ),
        ),
        "verification-redis": ServiceWithDefaults(
            image="redis:7-alpine",
            container_name="verification-redis",
            ports=["8009:6379"],
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "redis-cli", "ping"],
            ),
        ),
        "dependency-service": ServiceWithDefaults(
            build=BuildItemModernized(
                context="./dependency-service",
                additional_contexts=["common=./common"],
                dockerfile="Dockerfile",
            ),
            container_name="dependency-service",
            ports=["8001:8000"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
            ],
            depends_on={"postgres": {"condition": Condition.service_healthy}},
        ),
        "verification-service": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./verification-service",
            ),
            command=["python", "main_fastapi.py"],
            container_name="verification-service",
            ports=["8002:8000"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
            ],
            depends_on={
                "rabbitmq": {"condition": Condition.service_healthy},
                "verification-redis": {"condition": Condition.service_healthy},
            },
        ),
        "verification-worker": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./verification-service",
            ),
            command=["celery", "--app", "main_celery", "worker", "--loglevel=info"],
            container_name="verification-worker",
            ports=["8008:8000"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
            ],
            depends_on={
                "rabbitmq": {"condition": Condition.service_healthy},
                "verification-redis": {"condition": Condition.service_healthy},
            },
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "celery", "--app", "main_celery", "inspect", "ping"],
                timeout="2s",
            ),
            volumes=["/var/run/docker.sock:/var/run/docker.sock"],
        ),
        "verification-task": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./verification-task",
            ),
            deploy={"replicas": 0},
        ),
        "rabbitmq": ServiceWithDefaults(
            image="rabbitmq:4-management",
            container_name="rabbitmq",
            volumes=["./rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro"],
            ports=["8006:5672", "8007:15672"],
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "rabbitmq-diagnostics", "-q", "ping"],
            ),
        ),
        "pdf-service": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./pdf-service",
            ),
            container_name="pdf-service",
            ports=["8003:8000"],
            depends_on={"postgres": {"condition": Condition.service_healthy}},
        ),
        "latex-service": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./latex-service",
            ),
            container_name="latex-service",
            ports=["8004:8000"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
            ],
            depends_on={
                "postgres": {"condition": Condition.service_healthy},
                "pdf-service": {"condition": Condition.service_healthy},
            },
        ),
        "nginx": ServiceWithDefaults(
            image="nginx:latest",
            ports=["80:80"],
            volumes=["./nginx/nginx.conf:/etc/nginx/conf.d/default.conf"],
            depends_on={
                "dependency-service": {"condition": Condition.service_healthy},
                "verification-service": {"condition": Condition.service_healthy},
                "pdf-service": {"condition": Condition.service_healthy},
                "latex-service": {"condition": Condition.service_healthy},
            },
            healthcheck=None,
        ),
    }
    volumes: Optional[Dict[str, Optional[Dict]]] = {"pgdata": None}
    networks: Optional[Dict[str, Optional[Dict]]] = {"theorem-library": None}


compose_specification: DockerComposeConfig = DockerComposeConfig()
