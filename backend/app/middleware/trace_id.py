"""
Trace ID middleware for FastAPI.
Extracts or generates trace_id from X-Trace-ID header, injects into response.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.observability.logger import set_trace_id

if TYPE_CHECKING:
    from app.services.observability.logger import get_trace_id as _get_trace_id


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Middleware to manage trace_id for each request."""

    async def dispatch(self, request: Request, call_next):
        # Extract trace_id from header or generate a new one
        trace_id = request.headers.get("X-Trace-ID")
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # Set trace_id in ContextVar for async safety
        set_trace_id(trace_id)

        # Process request
        response = await call_next(request)

        # Inject trace_id into response headers
        response.headers["X-Trace-ID"] = trace_id

        return response
