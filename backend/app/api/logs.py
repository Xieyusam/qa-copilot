"""
Log query API for administrators.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer

from app.api.dependencies import require_admin
from app.config import settings
from app.services.observability.logger import get_trace_id

router = APIRouter()


def _parse_log_line(line: str) -> dict[str, Any] | None:
    """Parse a log line into a dictionary.

    Loguru text format: '2026-04-08 12:34:41.456 | INFO | module:function:line | message'
    We extract level, time, name, function, line, and message.
    """
    try:
        # 先尝试 JSON 格式
        return json.loads(line.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    # 解析 Text 格式: '2026-04-08 12:34:41.456 | LEVEL | name:func:line | message'
    try:
        parts = line.strip().split(" | ")
        if len(parts) >= 4:
            time_str = parts[0].strip()
            level = parts[1].strip()
            name_func_line = parts[2].strip()
            message = " | ".join(parts[3:]).strip()

            # 解析 name:function:line
            name_parts = name_func_line.rsplit(":", 2)
            name = name_func_line
            func = ""
            line_num = ""
            if len(name_parts) >= 3:
                name = name_parts[0]
                func = name_parts[1]
                line_num = name_parts[2]

            return {
                "time": time_str,
                "level": level,
                "name": name,
                "function": func,
                "line": line_num,
                "message": message,
                "trace_id": "",
            }
    except Exception:
        pass

    return None


def _filter_logs(
    logs: list[dict[str, Any]],
    level: str | None = None,
    trace_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> list[dict[str, Any]]:
    """Filter logs by criteria."""
    result = logs

    if level:
        result = [log for log in result if log.get("level", "").upper() == level.upper()]

    if trace_id:
        result = [log for log in result if trace_id in str(log.get("trace_id", ""))]

    if from_time:
        result = [
            log
            for log in result
            if datetime.fromisoformat(log.get("time", "1970-01-01T00:00:00").replace("Z", "+00:00"))
            >= from_time
        ]

    if to_time:
        result = [
            log
            for log in result
            if datetime.fromisoformat(log.get("time", "1970-01-01T00:00:00").replace("Z", "+00:00"))
            <= to_time
        ]

    return result


@router.get("/api/admin/logs")
async def query_logs(
    level: str | None = Query(None, description="Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    trace_id: str | None = Query(None, description="Filter by trace_id"),
    from_time: str | None = Query(None, description="Start time in ISO format"),
    to_time: str | None = Query(None, description="End time in ISO format"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    current_user: str = Depends(require_admin),
) -> list[dict[str, Any]]:
    """
    Query application logs with optional filters.

    Returns logs from the log directory, sorted by time descending.
    """
    log_dir = Path(settings.log_dir)

    if not log_dir.exists():
        return []

    # Parse time filters
    from_dt = None
    to_dt = None
    try:
        if from_time:
            from_dt = datetime.fromisoformat(from_time.replace("Z", "+00:00"))
        if to_time:
            to_dt = datetime.fromisoformat(to_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")

    # Find all log files
    log_files = sorted(log_dir.glob("app_*.log*"), reverse=True)

    all_logs: list[dict[str, Any]] = []

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    parsed = _parse_log_line(line)
                    if parsed:
                        all_logs.append(parsed)
        except (IOError, OSError):
            continue

    # Filter logs
    filtered_logs = _filter_logs(all_logs, level, trace_id, from_dt, to_dt)

    # Sort by time descending and limit
    filtered_logs.sort(key=lambda x: x.get("time", ""), reverse=True)

    return filtered_logs[:limit]


@router.get("/api/admin/logs/trace/{trace_id}")
async def get_logs_by_trace(
    trace_id: str,
    current_user: str = Depends(require_admin),
) -> dict[str, Any]:
    """
    Get all logs for a specific trace_id.

    Returns all log entries matching the trace_id.
    """
    log_dir = Path(settings.log_dir)

    if not log_dir.exists():
        return {"trace_id": trace_id, "logs": []}

    log_files = sorted(log_dir.glob("app_*.log*"), reverse=True)

    trace_logs: list[dict[str, Any]] = []

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    parsed = _parse_log_line(line)
                    if parsed and trace_id in str(parsed.get("trace_id", "")):
                        trace_logs.append(parsed)
        except (IOError, OSError):
            continue

    # Sort by time ascending
    trace_logs.sort(key=lambda x: x.get("time", ""))

    return {"trace_id": trace_id, "logs": trace_logs}
