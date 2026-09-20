"""
Prometheus metrics endpoint for the Kiosk Show Replacement application.

This module provides a /metrics endpoint that exposes application metrics
in Prometheus text format for monitoring and alerting.

Metrics exposed:
- http_requests_total: Total HTTP requests by method, endpoint, and status
- http_request_duration_seconds: Request duration histogram
- active_sse_connections: Current number of SSE connections
- database_errors_total: Count of database errors
- storage_errors_total: Count of storage errors
- display_heartbeat_age_seconds: Age of last display heartbeat
"""

import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from flask import Blueprint, Flask, Response, g, request

metrics_bp = Blueprint("metrics", __name__)

# Content type for the Prometheus text exposition format, version 0.0.4.
# The ``version`` parameter is required: Prometheus v3 fails a scrape whose
# Content-Type carries no recognized format version, where v2 silently fell
# back to this format. This is the same value as prometheus_client's
# ``CONTENT_TYPE_LATEST``.
PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class MetricsCollector:
    """Thread-safe metrics collector for Prometheus-style metrics."""

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._lock = threading.Lock()

        # Counters
        self._http_requests_total: Dict[Tuple[str, str, int], int] = defaultdict(int)
        self._database_errors_total: int = 0
        self._storage_errors_total: int = 0

        # Gauges
        self._active_sse_connections: int = 0

        # Histograms (simplified - just track sum and count per bucket)
        self._http_request_duration_sum: Dict[str, float] = defaultdict(float)
        self._http_request_duration_count: Dict[str, int] = defaultdict(int)
        self._http_request_duration_buckets: Dict[str, Dict[float, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Histogram bucket boundaries (in seconds)
        self._duration_buckets = [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
        ]

    def inc_http_requests(self, method: str, endpoint: str, status_code: int) -> None:
        """Increment HTTP request counter.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Request endpoint path
            status_code: HTTP response status code
        """
        with self._lock:
            self._http_requests_total[(method, endpoint, status_code)] += 1

    def observe_http_duration(self, endpoint: str, duration: float) -> None:
        """Record HTTP request duration.

        Args:
            endpoint: Request endpoint path
            duration: Request duration in seconds
        """
        with self._lock:
            self._http_request_duration_sum[endpoint] += duration
            self._http_request_duration_count[endpoint] += 1

            # Update histogram bucket - only increment the smallest bucket that fits
            for bucket in self._duration_buckets:
                if duration <= bucket:
                    self._http_request_duration_buckets[endpoint][bucket] += 1
                    break  # Only increment one bucket, cumulative is computed at output
            # Note: values larger than max bucket will only appear in +Inf

    def inc_database_errors(self) -> None:
        """Increment database error counter."""
        with self._lock:
            self._database_errors_total += 1

    def inc_storage_errors(self) -> None:
        """Increment storage error counter."""
        with self._lock:
            self._storage_errors_total += 1

    def set_sse_connections(self, count: int) -> None:
        """Set the number of active SSE connections.

        Args:
            count: Current number of active connections
        """
        with self._lock:
            self._active_sse_connections = count

    def get_metrics_text(self) -> str:
        """Generate Prometheus text format metrics.

        Returns:
            Metrics in Prometheus text exposition format
        """
        lines: List[str] = []

        with self._lock:
            # HTTP requests total
            lines.append("# HELP http_requests_total Total number of HTTP requests")
            lines.append("# TYPE http_requests_total counter")
            for (method, endpoint, status), count in sorted(
                self._http_requests_total.items()
            ):
                # Sanitize endpoint for label
                safe_endpoint = endpoint.replace('"', '\\"')
                lines.append(
                    f'http_requests_total{{method="{method}",endpoint="{safe_endpoint}",status="{status}"}} {count}'
                )

            # HTTP request duration
            lines.append("")
            lines.append(
                "# HELP http_request_duration_seconds HTTP request duration in seconds"
            )
            lines.append("# TYPE http_request_duration_seconds histogram")
            for endpoint in sorted(self._http_request_duration_sum.keys()):
                safe_endpoint = endpoint.replace('"', '\\"')
                # Bucket values
                cumulative = 0
                for bucket in self._duration_buckets:
                    cumulative += self._http_request_duration_buckets[endpoint].get(
                        bucket, 0
                    )
                    lines.append(
                        f'http_request_duration_seconds_bucket{{endpoint="{safe_endpoint}",le="{bucket}"}} {cumulative}'
                    )
                # +Inf bucket
                total_count = self._http_request_duration_count[endpoint]
                lines.append(
                    f'http_request_duration_seconds_bucket{{endpoint="{safe_endpoint}",le="+Inf"}} {total_count}'
                )
                # Sum and count
                lines.append(
                    f'http_request_duration_seconds_sum{{endpoint="{safe_endpoint}"}} {self._http_request_duration_sum[endpoint]:.6f}'
                )
                lines.append(
                    f'http_request_duration_seconds_count{{endpoint="{safe_endpoint}"}} {total_count}'
                )

            # Active SSE connections
            lines.append("")
            lines.append(
                "# HELP active_sse_connections Number of active SSE connections"
            )
            lines.append("# TYPE active_sse_connections gauge")
            lines.append(f"active_sse_connections {self._active_sse_connections}")

            # Database errors
            lines.append("")
            lines.append("# HELP database_errors_total Total number of database errors")
            lines.append("# TYPE database_errors_total counter")
            lines.append(f"database_errors_total {self._database_errors_total}")

            # Storage errors
            lines.append("")
            lines.append("# HELP storage_errors_total Total number of storage errors")
            lines.append("# TYPE storage_errors_total counter")
            lines.append(f"storage_errors_total {self._storage_errors_total}")

        return "\n".join(lines) + "\n"


# Global metrics collector instance
metrics_collector = MetricsCollector()


def init_metrics(app: Flask) -> None:
    """Initialize metrics collection middleware.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def start_timer() -> None:
        """Record request start time."""
        g.request_start_time = time.perf_counter()

    @app.after_request
    def record_metrics(response: Response) -> Response:
        """Record request metrics after each request."""
        # Skip metrics endpoint to avoid recursion
        if request.path == "/metrics":
            return response

        # Record request count
        endpoint = request.path
        method = request.method
        status_code = response.status_code
        metrics_collector.inc_http_requests(method, endpoint, status_code)

        # Record request duration
        start_time = getattr(g, "request_start_time", None)
        if start_time is not None:
            duration = time.perf_counter() - start_time
            metrics_collector.observe_http_duration(endpoint, duration)

        return response


def _escape_label_value(value: str) -> str:
    """Escape a label value for Prometheus text format.

    Args:
        value: The label value to escape

    Returns:
        Escaped label value safe for Prometheus format
    """
    # Escape backslashes first, then quotes, then newlines
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def get_display_heartbeat_metrics() -> str:
    """Get metrics for display heartbeat ages.

    Returns:
        Prometheus-formatted metrics for display heartbeats
    """
    try:
        from .models import Display

        lines: List[str] = []
        lines.append(
            "# HELP display_heartbeat_age_seconds Seconds since last display heartbeat"
        )
        lines.append("# TYPE display_heartbeat_age_seconds gauge")

        displays = Display.query.all()
        now = datetime.now(timezone.utc)

        for display in displays:
            if display.last_seen_at:
                age = (now - display.last_seen_at).total_seconds()
            else:
                age = -1  # Never seen

            safe_name = _escape_label_value(display.name)
            lines.append(
                f'display_heartbeat_age_seconds{{display_id="{display.id}",display_name="{safe_name}"}} {age:.1f}'
            )

        return "\n".join(lines) + "\n"
    except Exception:
        return ""


def get_display_metrics() -> str:
    """Get comprehensive metrics for all displays.

    Returns:
        Prometheus-formatted metrics for display information and status
    """
    try:
        from .models import Display

        lines: List[str] = []
        displays = Display.query.all()

        # display_info - info metric with slideshow labels
        lines.append(
            "# HELP display_info Display information metric (always 1) "
            "with slideshow assignment in labels"
        )
        lines.append("# TYPE display_info gauge")
        for display in displays:
            safe_name = _escape_label_value(display.name)
            slideshow_id = display.current_slideshow_id or ""
            slideshow_name = ""
            if display.current_slideshow:
                slideshow_name = _escape_label_value(display.current_slideshow.name)
            lines.append(
                f'display_info{{display_id="{display.id}",display_name="{safe_name}",'
                f'slideshow_id="{slideshow_id}",slideshow_name="{slideshow_name}"}} 1'
            )

        # display_online - 1 if online, 0 if offline
        lines.append("")
        lines.append(
            "# HELP display_online Display online status (1=online, 0=offline)"
        )
        lines.append("# TYPE display_online gauge")
        for display in displays:
            safe_name = _escape_label_value(display.name)
            online_val = 1 if display.is_online else 0
            lines.append(
                f'display_online{{display_id="{display.id}",'
                f'display_name="{safe_name}"}} {online_val}'
            )

        # display_resolution_width_pixels
        lines.append("")
        lines.append("# HELP display_resolution_width_pixels Display width in pixels")
        lines.append("# TYPE display_resolution_width_pixels gauge")
        for display in displays:
            if display.resolution_width is not None:
                safe_name = _escape_label_value(display.name)
                lines.append(
                    f'display_resolution_width_pixels{{display_id="{display.id}",'
                    f'display_name="{safe_name}"}} {display.resolution_width}'
                )

        # display_resolution_height_pixels
        lines.append("")
        lines.append("# HELP display_resolution_height_pixels Display height in pixels")
        lines.append("# TYPE display_resolution_height_pixels gauge")
        for display in displays:
            if display.resolution_height is not None:
                safe_name = _escape_label_value(display.name)
                lines.append(
                    f'display_resolution_height_pixels{{display_id="{display.id}",'
                    f'display_name="{safe_name}"}} {display.resolution_height}'
                )

        # display_rotation_degrees
        lines.append("")
        lines.append(
            "# HELP display_rotation_degrees Display rotation in degrees (0, 90, 180, 270)"
        )
        lines.append("# TYPE display_rotation_degrees gauge")
        for display in displays:
            safe_name = _escape_label_value(display.name)
            lines.append(
                f'display_rotation_degrees{{display_id="{display.id}",'
                f'display_name="{safe_name}"}} {display.rotation}'
            )

        # display_last_seen_timestamp_seconds
        lines.append("")
        lines.append(
            "# HELP display_last_seen_timestamp_seconds "
            "Unix timestamp of last display heartbeat"
        )
        lines.append("# TYPE display_last_seen_timestamp_seconds gauge")
        for display in displays:
            if display.last_seen_at:
                safe_name = _escape_label_value(display.name)
                last_seen = display.last_seen_at
                # Ensure timezone-aware
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                timestamp = last_seen.timestamp()
                lines.append(
                    f'display_last_seen_timestamp_seconds{{display_id="{display.id}",'
                    f'display_name="{safe_name}"}} {timestamp:.3f}'
                )

        # display_heartbeat_interval_seconds
        lines.append("")
        lines.append(
            "# HELP display_heartbeat_interval_seconds "
            "Configured heartbeat interval in seconds"
        )
        lines.append("# TYPE display_heartbeat_interval_seconds gauge")
        for display in displays:
            safe_name = _escape_label_value(display.name)
            lines.append(
                f'display_heartbeat_interval_seconds{{display_id="{display.id}",'
                f'display_name="{safe_name}"}} {display.heartbeat_interval}'
            )

        # display_missed_heartbeats
        lines.append("")
        lines.append("# HELP display_missed_heartbeats Number of missed heartbeats")
        lines.append("# TYPE display_missed_heartbeats gauge")
        for display in displays:
            safe_name = _escape_label_value(display.name)
            lines.append(
                f'display_missed_heartbeats{{display_id="{display.id}",'
                f'display_name="{safe_name}"}} {display.missed_heartbeats}'
            )

        # display_sse_connected - 1 if SSE connected, 0 if not
        lines.append("")
        lines.append(
            "# HELP display_sse_connected "
            "Display SSE connection status (1=connected, 0=disconnected)"
        )
        lines.append("# TYPE display_sse_connected gauge")
        for display in displays:
            safe_name = _escape_label_value(display.name)
            sse_val = 1 if display.sse_connected else 0
            lines.append(
                f'display_sse_connected{{display_id="{display.id}",'
                f'display_name="{safe_name}"}} {sse_val}'
            )

        # display_is_active - 1 if active, 0 if inactive
        lines.append("")
        lines.append(
            "# HELP display_is_active Display active status (1=active, 0=inactive)"
        )
        lines.append("# TYPE display_is_active gauge")
        for display in displays:
            safe_name = _escape_label_value(display.name)
            active_val = 1 if display.is_active else 0
            lines.append(
                f'display_is_active{{display_id="{display.id}",'
                f'display_name="{safe_name}"}} {active_val}'
            )

        return "\n".join(lines) + "\n"
    except Exception:
        return ""


def get_summary_metrics() -> str:
    """Get summary/aggregate metrics for displays and slideshows.

    Returns:
        Prometheus-formatted metrics for summary counts
    """
    try:
        from .models import Display, Slideshow

        lines: List[str] = []

        # Total displays count
        displays = Display.query.all()
        total_displays = len(displays)
        online_displays = sum(1 for d in displays if d.is_online)
        active_displays = sum(1 for d in displays if d.is_active)

        lines.append("# HELP displays_total Total number of displays")
        lines.append("# TYPE displays_total gauge")
        lines.append(f"displays_total {total_displays}")

        lines.append("")
        lines.append("# HELP displays_online_total Number of displays currently online")
        lines.append("# TYPE displays_online_total gauge")
        lines.append(f"displays_online_total {online_displays}")

        lines.append("")
        lines.append(
            "# HELP displays_active_total Number of active (not disabled) displays"
        )
        lines.append("# TYPE displays_active_total gauge")
        lines.append(f"displays_active_total {active_displays}")

        # Total slideshows count
        total_slideshows = Slideshow.query.count()
        lines.append("")
        lines.append("# HELP slideshows_total Total number of slideshows")
        lines.append("# TYPE slideshows_total gauge")
        lines.append(f"slideshows_total {total_slideshows}")

        return "\n".join(lines) + "\n"
    except Exception:
        return ""


def get_sse_connection_metrics() -> None:
    """Update SSE connection count metric."""
    try:
        from .sse import sse_manager

        stats = sse_manager.get_connection_stats()
        metrics_collector.set_sse_connections(stats.get("total_connections", 0))
    except Exception:
        pass


@metrics_bp.route("/metrics")
def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus text exposition format.
    """
    # Update dynamic metrics
    get_sse_connection_metrics()

    # Collect all metrics
    output = metrics_collector.get_metrics_text()

    # Add display heartbeat metrics
    output += "\n" + get_display_heartbeat_metrics()

    # Add comprehensive display metrics
    output += "\n" + get_display_metrics()

    # Add summary metrics
    output += "\n" + get_summary_metrics()

    # Use content_type rather than mimetype: Werkzeug appends its own
    # charset to a mimetype, which would duplicate the parameter here.
    return Response(output, content_type=PROMETHEUS_CONTENT_TYPE)


# Convenience functions for recording metrics from other modules
def record_database_error() -> None:
    """Record a database error occurrence."""
    metrics_collector.inc_database_errors()


def record_storage_error() -> None:
    """Record a storage error occurrence."""
    metrics_collector.inc_storage_errors()
