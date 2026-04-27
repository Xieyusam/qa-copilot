"""
Prometheus metrics endpoint.
"""
from __future__ import annotations

from starlette.responses import Response

from fastapi import APIRouter

from app.services.observability.metrics import format_prometheus_text

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint in text exposition format.

    Returns:
        Prometheus metrics in text format
    """
    content = format_prometheus_text()
    return Response(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
