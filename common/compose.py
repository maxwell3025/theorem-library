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
        "neo4j": ServiceWithDefaults(
            image="neo4j:5",
            container_name="neo4j",
            volumes=["neo4j_data:/data", "neo4j_logs:/logs"],
            ports=[
                "8011:7474",
                "8010:7687",
            ],  # 7474 for browser dashboard, 7687 for bolt protocol
            environment=[
                "NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASSWORD}",
                "NEO4J_server_memory_heap_initial__size=512m",
                "NEO4J_server_memory_heap_max__size=2G",
            ],
            healthcheck=HealthcheckWithDefaults(
                test=[
                    "CMD",
                    "cypher-shell",
                    "-u",
                    "neo4j",
                    "-p",
                    "${NEO4J_PASSWORD}",
                    "RETURN 1",
                ],
                interval="5s",
                timeout="3s",
                retries=5,
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
                "NEO4J_USER=${NEO4J_USER}",
                "NEO4J_PASSWORD=${NEO4J_PASSWORD}",
            ],
            depends_on={
                "neo4j": {"condition": Condition.service_healthy},
                "dependency-worker": {"condition": Condition.service_healthy},
            },
        ),
        "dependency-worker": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./dependency-service",
            ),
            command=[
                "celery",
                "--app",
                "main_celery",
                "worker",
                "--loglevel=info",
                "-Q",
                "dependency",
            ],
            container_name="dependency-worker",
            ports=["8012:8000"],
            environment=[
                "NEO4J_USER=${NEO4J_USER}",
                "NEO4J_PASSWORD=${NEO4J_PASSWORD}",
            ],
            depends_on={
                "rabbitmq": {"condition": Condition.service_healthy},
            },
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "celery", "--app", "main_celery", "inspect", "ping"],
                timeout="2s",
            ),
            volumes=["/var/run/docker.sock:/var/run/docker.sock"],
        ),
        "dependency-task": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./dependency-task",
            ),
            deploy={"replicas": 0},
        ),
        "verification-redis": ServiceWithDefaults(
            image="redis:7-alpine",
            container_name="verification-redis",
            ports=["8009:6379"],
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "redis-cli", "ping"],
            ),
        ),
        "verification-service": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./verification-service",
            ),
            command=["python", "main_fastapi.py"],
            container_name="verification-service",
            ports=["8002:8000"],
            depends_on={
                "rabbitmq": {"condition": Condition.service_healthy},
                "verification-redis": {"condition": Condition.service_healthy},
            },
        ),
        "verification-worker": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./verification-service",
            ),
            command=[
                "celery",
                "--app",
                "main_celery",
                "worker",
                "--loglevel=info",
                "-Q",
                "verification",
            ],
            container_name="verification-worker",
            ports=["8008:8000"],
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
            volumes=["pdf_data:/data"],
        ),
        "latex-redis": ServiceWithDefaults(
            image="redis:7-alpine",
            container_name="latex-redis",
            ports=["8015:6379"],
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "redis-cli", "ping"],
            ),
        ),
        "latex-service": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./latex-service",
            ),
            command=["python", "main.py"],
            container_name="latex-service",
            ports=["8004:8000"],
            depends_on={
                "rabbitmq": {"condition": Condition.service_healthy},
                "latex-redis": {"condition": Condition.service_healthy},
            },
        ),
        "latex-worker": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./latex-service",
            ),
            command=[
                "celery",
                "--app",
                "main_celery",
                "worker",
                "--loglevel=info",
                "-Q",
                "latex",
            ],
            container_name="latex-worker",
            ports=["8013:8000"],
            depends_on={
                "rabbitmq": {"condition": Condition.service_healthy},
                "latex-redis": {"condition": Condition.service_healthy},
            },
            restart="unless-stopped",
            healthcheck=HealthcheckWithDefaults(
                test=["CMD", "celery", "--app", "main_celery", "inspect", "ping"],
                timeout="2s",
            ),
            volumes=["/var/run/docker.sock:/var/run/docker.sock"],
        ),
        "latex-task": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./latex-task",
            ),
            deploy={"replicas": 0},
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
        "git-server": ServiceWithDefaults(
            build=BuildItemWithDefaults(
                context="./git-server",
                additional_contexts=[],
            ),
            container_name="git-server",
            ports=["8005:8000"],
            healthcheck=HealthcheckWithDefaults(
                test=[
                    "CMD",
                    "wget",
                    "--no-verbose",
                    "--tries=1",
                    "--spider",
                    "http://127.0.0.1:8000/health",
                ],
            ),
        ),
    }
    volumes: Optional[Dict[str, Optional[Dict]]] = {
        "neo4j_data": None,
        "neo4j_logs": None,
        "pdf_data": None,
    }
    networks: Optional[Dict[str, Optional[Dict]]] = {"theorem-library": None}


compose_specification: DockerComposeConfig = DockerComposeConfig()
