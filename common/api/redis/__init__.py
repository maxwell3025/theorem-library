import redis
import common.model as model
import time
from common.config import config


def check_health(timeout: float = 5) -> model.HealthCheckDependency:
    """Check health of Redis connection."""
    backup_timer_start = time.perf_counter()
    try:
        r = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
        )
        start_time = time.perf_counter()
        r.ping()
        end_time = time.perf_counter()
        response_time_ms = int((end_time - start_time) * 1000)
        r.close()
        return model.HealthCheckDependency(
            status="healthy", response_time_ms=response_time_ms
        )
    except redis.exceptions.TimeoutError:
        return model.HealthCheckDependency(status="timeout", response_time_ms=None)
    except Exception:
        backup_timer_end = time.perf_counter()
        response_time_ms = int((backup_timer_end - backup_timer_start) * 1000)
        return model.HealthCheckDependency(
            status="unhealthy", response_time_ms=response_time_ms
        )


def get_redis_client() -> redis.Redis:
    """Get a Redis client connection."""
    return redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        decode_responses=True,
    )
