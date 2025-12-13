import httpx
import common.model as model
import time
from . import neo4j


def check_service_health(service_base: str, timeout: float = 5):
    # backup in case httpx method fails -- this still allows us to get a timestamp
    backup_timer_start = time.perf_counter()
    try:
        response = httpx.get(f"{service_base}/health", timeout=timeout)
        response_time_ms = response.elapsed.microseconds // 1000
        status: model.DependencyHealthCheckStatus = (
            "healthy" if response.status_code == 200 else "unhealthy"
        )
        return model.HealthCheckDependency(
            status=status, response_time_ms=response_time_ms
        )
    except httpx.TimeoutException:
        return model.HealthCheckDependency(status="timeout", response_time_ms=None)
    except:
        # we consider the service unhealthy if there is some other issue with the healthcheck
        backup_timer_end = time.perf_counter()
        response_time_ms = int((backup_timer_end - backup_timer_start) * 1000)
        return model.HealthCheckDependency(
            status="unhealthy", response_time_ms=response_time_ms
        )
