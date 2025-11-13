import typing
import common.model


class HealthCheckResponse(common.model.HealthCheckResponse):
    service: typing.Literal["latex-service"] = "latex-service"
