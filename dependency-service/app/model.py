import typing
import common.model


class HealthCheckResponse(common.model.HealthCheckResponse):
    service: typing.Literal["dependency-service"] = "dependency-service"
