from pydantic import BaseModel


class Neo4jConfig(BaseModel):
    """Neo4j database configuration (non-sensitive)."""

    host: str = "neo4j"
    bolt_port: str = "7687"
    http_port: str = "7474"
    database: str = "neo4j"


class VerificationConfig(BaseModel):
    """Docker container configuration."""

    verification_task_name: str = "verification-task"


class RedisConfig(BaseModel):
    """Redis configuration for verification service."""

    host: str = "verification-redis"
    port: int = 6379


class ServiceConfig(BaseModel):
    """External service URLs and endpoints."""

    pdf_service_base: str = "http://pdf-service:8000"


class AppConfig(BaseModel):
    """Global application configuration."""

    project_name: str = "theorem-library"
    neo4j: Neo4jConfig = Neo4jConfig()
    verification_config: VerificationConfig = VerificationConfig()
    redis: RedisConfig = RedisConfig()
    services: ServiceConfig = ServiceConfig()


# Global configuration instance
config = AppConfig()
