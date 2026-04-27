"""
Prometheus metrics for QA Copilot observability.
"""
from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Any

# Simple in-memory metrics store (thread-safe)
class MetricsStore:
    """Thread-safe in-memory metrics store."""

    def __init__(self):
        self._lock = Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}

    def inc_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe a value for a histogram metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get current counter value."""
        key = self._make_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_histogram_stats(self, name: str, labels: dict[str, str] | None = None) -> dict[str, float]:
        """Get histogram statistics (count, sum, avg)."""
        key = self._make_key(name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {"count": 0, "sum": 0.0, "avg": 0.0}
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
            }

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float | None:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            return self._gauges.get(key)

    def _make_key(self, name: str, labels: dict[str, str] | None) -> str:
        """Create a composite key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def collect_all(self) -> dict[str, Any]:
        """Collect all metrics for Prometheus export."""
        with self._lock:
            result = {
                "counters": dict(self._counters),
                "histograms": {},
                "gauges": dict(self._gauges),
            }
            for key, values in self._histograms.items():
                if values:
                    result["histograms"][key] = {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values),
                    }
            return result


# Global metrics store instance
_metrics_store = MetricsStore()


# =============================================================================
# Metric Definitions
# =============================================================================

# Counter: Total copilot requests
COPILOT_REQUESTS_TOTAL = "copilot_requests_total"

# Histogram: Copilot request duration in seconds
COPILOT_REQUEST_DURATION_SECONDS = "copilot_request_duration_seconds"

# Counter: Total tool calls (by tool_name)
TOOL_CALLS_TOTAL = "tool_calls_total"

# Counter: Document processing (by status: success/failed)
DOCUMENT_PROCESSING_TOTAL = "document_processing_total"

# Histogram: Document processing duration in seconds
DOCUMENT_PROCESSING_DURATION_SECONDS = "document_processing_duration_seconds"

# Counter: Jira queries total
JIRA_QUERIES_TOTAL = "jira_queries_total"

# Gauge: Active sessions
ACTIVE_SESSIONS = "active_sessions"


# =============================================================================
# Public API Functions
# =============================================================================

def increment_counter(name: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
    """
    Increment a counter metric.

    Args:
        name: Metric name
        labels: Optional label dictionary
        value: Value to increment by (default 1.0)
    """
    _metrics_store.inc_counter(name, value, labels)


def observe_histogram(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """
    Observe a value for a histogram metric.

    Args:
        name: Metric name
        value: Value to observe
        labels: Optional label dictionary
    """
    _metrics_store.observe_histogram(name, value, labels)


def set_gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """
    Set a gauge metric value.

    Args:
        name: Metric name
        value: Value to set
        labels: Optional label dictionary
    """
    _metrics_store.set_gauge(name, value, labels)


def get_metrics() -> dict[str, Any]:
    """
    Get all collected metrics.

    Returns:
        Dictionary containing all metrics in Prometheus format
    """
    return _metrics_store.collect_all()


def format_prometheus_text() -> str:
    """
    Format metrics as Prometheus text exposition format.

    Returns:
        Prometheus text format string
    """
    metrics = _metrics_store.collect_all()
    lines = []

    # Format counters
    for key, value in sorted(metrics["counters"].items()):
        lines.append(f"# HELP {key} Counter metric {key}")
        lines.append(f"# TYPE {key} counter")
        lines.append(f"{key} {value}")

    # Format histograms (as simple gauges for count/sum)
    for key, stats in sorted(metrics["histograms"].items()):
        hist_name = f"{key}_count"
        lines.append(f"# HELP {hist_name} Histogram metric {key} count")
        lines.append(f"# TYPE {hist_name} gauge")
        lines.append(f"{hist_name} {stats['count']}")

        hist_name_sum = f"{key}_sum"
        lines.append(f"# HELP {hist_name_sum} Histogram metric {key} sum")
        lines.append(f"# TYPE {hist_name_sum} gauge")
        lines.append(f"{hist_name_sum} {stats['sum']}")

    # Format gauges
    for key, value in sorted(metrics["gauges"].items()):
        lines.append(f"# HELP {key} Gauge metric {key}")
        lines.append(f"# TYPE {key} gauge")
        lines.append(f"{key} {value}")

    return "\n".join(lines) + "\n"
