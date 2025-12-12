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


class AppConfig(BaseModel):
    """Global application configuration."""
    postgres: PostgresConfig = PostgresConfig()
    docker: DockerConfig = DockerConfig()
    services: ServiceConfig = ServiceConfig()


# Global configuration instance
config = AppConfig()
