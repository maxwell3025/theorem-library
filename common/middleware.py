import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures all requests have a correlation ID for tracking.
    
    If a request doesn't include an X-Correlation-ID header, one is generated.
    The correlation ID is added to both the request headers and response headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        if request.headers.get("X-Correlation-ID") is None:
            logger.warning(
                f"Received request without header X-Correlation-ID. Setting X-Correlation-ID={correlation_id}"
            )

        # Set the correlation ID in the request so that the request handler can safely depend on the header.
        # This is done unconditionally, since it should do nothing if X-Correlation-ID is already set.
        headers = request.headers.mutablecopy()
        headers["X-Correlation-ID"] = correlation_id
        request.scope["headers"] = headers.raw

        response: Response = await call_next(request)

        response.headers["X-Correlation-ID"] = correlation_id

        return response
