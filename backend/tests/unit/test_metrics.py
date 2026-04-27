"""
Tests for metrics service.
"""
from __future__ import annotations

import pytest
from app.services.observability.metrics import (
    MetricsStore,
    increment_counter,
    observe_histogram,
    set_gauge,
    get_metrics,
    format_prometheus_text,
    _metrics_store,
)


class TestMetricsStore:
    """Test MetricsStore thread-safe operations."""

    def test_inc_counter_basic(self):
        store = MetricsStore()
        store.inc_counter("test_counter")
        assert store.get_counter("test_counter") == 1.0

    def test_inc_counter_with_labels(self):
        store = MetricsStore()
        store.inc_counter("test_counter", labels={"method": "GET"})
        store.inc_counter("test_counter", labels={"method": "POST"})
        assert store.get_counter("test_counter", {"method": "GET"}) == 1.0
        assert store.get_counter("test_counter", {"method": "POST"}) == 1.0

    def test_inc_counter_increments_by_value(self):
        store = MetricsStore()
        store.inc_counter("test_counter", value=5.0)
        assert store.get_counter("test_counter") == 5.0

    def test_inc_counter_multiple_times(self):
        store = MetricsStore()
        store.inc_counter("test_counter")
        store.inc_counter("test_counter")
        store.inc_counter("test_counter")
        assert store.get_counter("test_counter") == 3.0

    def test_observe_histogram_basic(self):
        store = MetricsStore()
        store.observe_histogram("test_histogram", 0.5)
        stats = store.get_histogram_stats("test_histogram")
        assert stats["count"] == 1
        assert stats["sum"] == 0.5

    def test_observe_histogram_multiple_values(self):
        store = MetricsStore()
        store.observe_histogram("test_histogram", 0.1)
        store.observe_histogram("test_histogram", 0.2)
        store.observe_histogram("test_histogram", 0.3)
        stats = store.get_histogram_stats("test_histogram")
        assert stats["count"] == 3
        assert abs(stats["sum"] - 0.6) < 1e-9
        assert abs(stats["avg"] - 0.2) < 1e-9

    def test_observe_histogram_empty(self):
        store = MetricsStore()
        stats = store.get_histogram_stats("nonexistent")
        assert stats == {"count": 0, "sum": 0.0, "avg": 0.0}

    def test_set_gauge_basic(self):
        store = MetricsStore()
        store.set_gauge("test_gauge", 42.0)
        assert store.get_gauge("test_gauge") == 42.0

    def test_set_gauge_updates_value(self):
        store = MetricsStore()
        store.set_gauge("test_gauge", 10.0)
        store.set_gauge("test_gauge", 20.0)
        assert store.get_gauge("test_gauge") == 20.0

    def test_set_gauge_with_labels(self):
        store = MetricsStore()
        store.set_gauge("test_gauge", 100.0, labels={"host": "localhost"})
        assert store.get_gauge("test_gauge", {"host": "localhost"}) == 100.0

    def test_get_counter_nonexistent_returns_zero(self):
        store = MetricsStore()
        assert store.get_counter("nonexistent") == 0.0

    def test_get_gauge_nonexistent_returns_none(self):
        store = MetricsStore()
        assert store.get_gauge("nonexistent") is None

    def test_collect_all(self):
        store = MetricsStore()
        store.inc_counter("c1")
        store.observe_histogram("h1", 1.0)
        store.set_gauge("g1", 5.0)
        result = store.collect_all()
        assert "c1" in result["counters"]
        assert "h1" in result["histograms"]
        assert "g1" in result["gauges"]


class TestPublicMetricsAPI:
    """Test public metrics API functions."""

    def test_increment_counter(self):
        _metrics_store._counters.clear()
        increment_counter("api_test_counter", value=1.0)
        assert _metrics_store.get_counter("api_test_counter") == 1.0

    def test_observe_histogram(self):
        _metrics_store._histograms.clear()
        observe_histogram("api_test_histogram", 0.5)
        stats = _metrics_store.get_histogram_stats("api_test_histogram")
        assert stats["count"] == 1

    def test_set_gauge(self):
        _metrics_store._gauges.clear()
        set_gauge("api_test_gauge", 99.0)
        assert _metrics_store.get_gauge("api_test_gauge") == 99.0

    def test_get_metrics_returns_dict(self):
        _metrics_store._counters.clear()
        _metrics_store._histograms.clear()
        _metrics_store._gauges.clear()
        result = get_metrics()
        assert isinstance(result, dict)
        assert "counters" in result
        assert "histograms" in result
        assert "gauges" in result


class TestPrometheusTextFormat:
    """Test Prometheus text format output."""

    def test_format_prometheus_text_returns_string(self):
        result = format_prometheus_text()
        assert isinstance(result, str)

    def test_format_prometheus_text_contains_metrics(self):
        # Add some metrics first
        _metrics_store._counters.clear()
        _metrics_store._histograms.clear()
        _metrics_store._gauges.clear()
        increment_counter("prom_test_counter", value=10.0)
        set_gauge("prom_test_gauge", 5.0)
        observe_histogram("prom_test_histogram", 0.5)
        result = format_prometheus_text()
        assert "prom_test_counter" in result
        assert "prom_test_gauge" in result
        assert "prom_test_histogram" in result

    def test_format_prometheus_text_empty_metrics(self):
        _metrics_store._counters.clear()
        _metrics_store._histograms.clear()
        _metrics_store._gauges.clear()
        result = format_prometheus_text()
        assert isinstance(result, str)
        # Should just have HELP/TYPE lines, no metric values
