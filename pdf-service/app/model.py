import typing
import common.model


class HealthCheckResponse(common.model.HealthCheckResponse):
    service: typing.Literal["pdf-service"] = "pdf-service"
