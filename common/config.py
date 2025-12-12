from pydantic import BaseModel


class PostgresConfig(BaseModel):
    """PostgreSQL database configuration (non-sensitive)."""

    host: str = "postgres"
    port: str = "5432"
    database: str = "theorem_library"


class VerificationConfig(BaseModel):
    """Docker container configuration."""

    verification_task_name: str = "verification-task"


class ServiceConfig(BaseModel):
    """External service URLs and endpoints."""

    pdf_service_base: str = "http://pdf-service:8000"


class AppConfig(BaseModel):
    """Global application configuration."""

    project_name: str = "theorem-library"
    postgres: PostgresConfig = PostgresConfig()
    verification_config: VerificationConfig = VerificationConfig()
    services: ServiceConfig = ServiceConfig()


# Global configuration instance
config = AppConfig()
