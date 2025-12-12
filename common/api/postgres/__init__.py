import common.model
import common.config
import time
import psycopg
import os

# Sensitive credentials from environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER", default="postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", default="")

# Non-sensitive config from typed configuration
POSTGRES_DB = common.config.config.postgres.database
POSTGRES_HOST = common.config.config.postgres.host
POSTGRES_PORT = common.config.config.postgres.port


def check_health() -> common.model.HealthCheckDependency:
    database_status: common.model.DependencyHealthCheckStatus = "unhealthy"
    connection = None
    # Attempt a connection to the Postgres database to check if it is healthy
    # TODO Check if there is a less intrusive healthcheck
    # For instance, this can fail if the database is alive, but simply has exhausted its connections
    try:
        timer_start = time.perf_counter()
        connection = psycopg.connect(
            f"host={POSTGRES_HOST} user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
        )
        timer_end = time.perf_counter()
        response_time = int((timer_end - timer_start) * 1000)
        database_status = "healthy"
    finally:
        if connection:
            connection.close()

    return common.model.HealthCheckDependency(
        status=database_status, response_time_ms=response_time
    )
