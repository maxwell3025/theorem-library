from pydantic import BaseModel


class PostgresConfig(BaseModel):
    """PostgreSQL database configuration (non-sensitive)."""

    host: str = "postgres"
    port: str = "5432"
    database: str = "theorem_library"


class DockerConfig(BaseModel):
    """Docker container configuration."""

    verification_task_name: str = "verification-task"
    project_name: str = "theorem-library"


class ServiceConfig(BaseModel):
    """External service URLs and endpoints."""

    pdf_service_base: str = "http://pdf-service:8000"


class BaseHealthCheckConfig(BaseModel):
    """Base Docker healthcheck configuration."""

    interval: str = "1s"
    timeout: str = "1s"
    retries: int = 10
    start_period: str = "1s"


class PostgresHealthCheckConfig(BaseHealthCheckConfig):
    """PostgreSQL healthcheck configuration."""

    pass


class DependencyServiceHealthCheckConfig(BaseHealthCheckConfig):
    """Dependency service healthcheck configuration."""

    pass


class VerificationServiceHealthCheckConfig(BaseHealthCheckConfig):
    """Verification service healthcheck configuration."""

    pass


class VerificationWorkerHealthCheckConfig(BaseHealthCheckConfig):
    """Verification worker healthcheck configuration."""

    pass


class RabbitMQHealthCheckConfig(BaseHealthCheckConfig):
    """RabbitMQ healthcheck configuration."""

    pass


class PdfServiceHealthCheckConfig(BaseHealthCheckConfig):
    """PDF service healthcheck configuration."""

    pass


class LatexServiceHealthCheckConfig(BaseHealthCheckConfig):
    """LaTeX service healthcheck configuration."""

    pass


class AppConfig(BaseModel):
    """Global application configuration."""

    postgres: PostgresConfig = PostgresConfig()
    docker: DockerConfig = DockerConfig()
    services: ServiceConfig = ServiceConfig()
    postgres_healthcheck: PostgresHealthCheckConfig = PostgresHealthCheckConfig()
    dependency_service_healthcheck: DependencyServiceHealthCheckConfig = (
        DependencyServiceHealthCheckConfig()
    )
    verification_service_healthcheck: VerificationServiceHealthCheckConfig = (
        VerificationServiceHealthCheckConfig()
    )
    verification_worker_healthcheck: VerificationWorkerHealthCheckConfig = (
        VerificationWorkerHealthCheckConfig()
    )
    rabbitmq_healthcheck: RabbitMQHealthCheckConfig = RabbitMQHealthCheckConfig()
    pdf_service_healthcheck: PdfServiceHealthCheckConfig = PdfServiceHealthCheckConfig()
    latex_service_healthcheck: LatexServiceHealthCheckConfig = (
        LatexServiceHealthCheckConfig()
    )


# Global configuration instance
config = AppConfig()
