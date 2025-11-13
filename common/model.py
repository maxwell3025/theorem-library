import pydantic
import typing

HealthCheckStatus = typing.Literal["healthy", "unhealthy"]
DependencyHealthCheckStatus = typing.Literal["healthy", "unhealthy", "timeout"]


class HealthCheckDependency(pydantic.BaseModel):
    status: DependencyHealthCheckStatus
    response_time_ms: typing.Optional[int]


class HealthCheckResponse(pydantic.BaseModel):
    status: HealthCheckStatus
    service: str
    dependencies: typing.Dict[
        str, HealthCheckDependency
    ]  # Can't be fully typed since dependencies have hyphenated names
