from typing import Dict, Optional
from compose_pydantic import (
    ComposeSpecification,
    Service,
    BuildItem,
    Healthcheck,
    Condition,
)


class HealthcheckWithDefaults(Healthcheck):
    """Base Docker healthcheck configuration."""

    interval: str = "1s"
    retries: float = 10
    timeout: str = "1s"
    start_period: str = "1s"


class BuildItemModernized(BuildItem):
    """Build item with modernized field names."""

    additional_contexts: Optional[list[str]] = None


class ServiceModernized(Service):
    """Service with modernized field names."""

    build: Optional[BuildItemModernized] = None


class DockerComposeConfig(ComposeSpecification):
    """Docker Compose configuration using compose-pydantic."""

    name: str = "${DOCKER_PROJECT_NAME}"
    services: Dict[str, ServiceModernized] = {
        "postgres": ServiceModernized(
            image="postgres:18",
            container_name="postgres",
            volumes=["pgdata:/var/lib/postgresql"],
            ports=["8000:${POSTGRES_PORT}"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
                "POSTGRES_DB=${POSTGRES_DATABASE}",
            ],
            restart="unless-stopped",
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
            networks=["theorem-library"],
        ),
        "dependency-service": ServiceModernized(
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
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "httpx", "http://localhost:8000/health"],
            ),
            networks=["theorem-library"],
        ),
        "verification-service": ServiceModernized(
            build=BuildItemModernized(
                context="./verification-service",
                additional_contexts=["common=./common"],
                dockerfile="Dockerfile",
            ),
            command=["python", "main_fastapi.py"],
            container_name="verification-service",
            ports=["8002:8000"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
            ],
            depends_on={
                "postgres": {"condition": Condition.service_healthy},
                "rabbitmq": {"condition": Condition.service_healthy},
            },
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "httpx", "http://localhost:8000/health"],
            ),
            networks=["theorem-library"],
        ),
        "verification-worker": ServiceModernized(
            build=BuildItemModernized(
                context="./verification-service",
                additional_contexts=["common=./common"],
                dockerfile="Dockerfile",
            ),
            command=["celery", "--app", "main_celery", "worker", "--loglevel=info"],
            container_name="verification-worker",
            ports=["8008:8000"],
            environment=[
                "POSTGRES_USER=${POSTGRES_USER}",
                "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
            ],
            depends_on={
                "postgres": {"condition": Condition.service_healthy},
                "rabbitmq": {"condition": Condition.service_healthy},
            },
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "celery", "--app", "main_celery", "inspect", "ping"],
                timeout="2s",
            ),
            networks=["theorem-library"],
            volumes=["/var/run/docker.sock:/var/run/docker.sock"],
        ),
        "verification-task": ServiceModernized(
            build=BuildItemModernized(
                context="./verification-task",
                additional_contexts=["common=./common"],
                dockerfile="Dockerfile",
            ),
            deploy={"replicas": 0},
        ),
        "rabbitmq": ServiceModernized(
            image="rabbitmq:4-management",
            container_name="rabbitmq",
            volumes=["./rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro"],
            ports=["8006:5672", "8007:15672"],
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "rabbitmq-diagnostics", "-q", "ping"],
            ),
            networks=["theorem-library"],
        ),
        "pdf-service": ServiceModernized(
            build=BuildItemModernized(
                context="./pdf-service",
                additional_contexts=["common=./common"],
                dockerfile="Dockerfile",
            ),
            container_name="pdf-service",
            ports=["8003:8000"],
            environment=["SERVICES_PDF_SERVICE_BASE=${SERVICES_PDF_SERVICE_BASE}"],
            depends_on={"postgres": {"condition": "service_healthy"}},
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "httpx", "http://localhost:8000/health"],
            ),
            networks=["theorem-library"],
        ),
        "latex-service": ServiceModernized(
            build=BuildItemModernized(
                context="./latex-service",
                additional_contexts=["common=./common"],
                dockerfile="Dockerfile",
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
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "httpx", "http://localhost:8000/health"],
            ),
            networks=["theorem-library"],
        ),
        "nginx": ServiceModernized(
            image="nginx:latest",
            ports=["80:80"],
            volumes=["./nginx/nginx.conf:/etc/nginx/conf.d/default.conf"],
            networks=["theorem-library"],
            depends_on={
                "dependency-service": {"condition": Condition.service_healthy},
                "verification-service": {"condition": Condition.service_healthy},
                "pdf-service": {"condition": Condition.service_healthy},
                "latex-service": {"condition": Condition.service_healthy},
            },
        ),
    }
    volumes: Optional[Dict[str, Optional[Dict]]] = {"pgdata": None}
    networks: Optional[Dict[str, Optional[Dict]]] = {"theorem-library": None}


compose_specification: DockerComposeConfig = DockerComposeConfig()
