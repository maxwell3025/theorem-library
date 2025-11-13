import common.model
import time
import psycopg
import os

POSTGRES_USER = os.getenv("POSTGRES_USER", default="postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", default="")
POSTGRES_DB = os.getenv("POSTGRES_DB", default="theorem_library")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", default="postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", default="5432")


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
