import common.model
import common.config
import time
import os
from neo4j import GraphDatabase

# Sensitive credentials from environment variables
NEO4J_USER = os.getenv("NEO4J_USER", default="neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", default="")

# Non-sensitive config from typed configuration
NEO4J_HOST = common.config.config.neo4j.host
NEO4J_BOLT_PORT = common.config.config.neo4j.bolt_port
NEO4J_URI = f"bolt://{NEO4J_HOST}:{NEO4J_BOLT_PORT}"


def check_health() -> common.model.HealthCheckDependency:
    database_status: common.model.DependencyHealthCheckStatus = "unhealthy"
    driver = None
    response_time = 0
    # Attempt a connection to the Neo4j database to check if it is healthy
    try:
        timer_start = time.perf_counter()
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        # Verify connectivity
        driver.verify_connectivity()
        timer_end = time.perf_counter()
        response_time = int((timer_end - timer_start) * 1000)
        database_status = "healthy"
    except Exception:
        pass
    finally:
        if driver:
            driver.close()

    return common.model.HealthCheckDependency(
        status=database_status, response_time_ms=response_time
    )
