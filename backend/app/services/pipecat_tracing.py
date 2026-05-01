"""Optional Pipecat OpenTelemetry bootstrap for voice-bot subprocesses.

Follows Pipecat guidance: initialize the OTEL SDK with an exporter, then enable
tracing on ``PipelineTask``. RTVI/TTFB metrics are enabled on the task separately for all sessions.

References:
- https://docs.pipecat.ai/api-reference/server/utilities/opentelemetry
"""
from __future__ import annotations

import logging
import os
from typing import Final

_logger = logging.getLogger(__name__)

_TRUTHY: Final = frozenset({"1", "true", "yes", "on"})


def tracing_enabled_from_env() -> bool:
    return os.getenv("ENABLE_TRACING", "").strip().lower() in _TRUTHY


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in _TRUTHY


def _build_otlp_exporter():
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317").strip()
    protocol = os.getenv("OTEL_EXPORTER_OTLP_TRACES_PROTOCOL", "").strip().lower()

    if protocol in ("http/protobuf", "http/json"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter(endpoint=endpoint)

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    insecure = _env_bool("OTEL_EXPORTER_OTLP_INSECURE", True)
    return OTLPSpanExporter(endpoint=endpoint, insecure=insecure)


def configure_pipecat_tracing_from_env() -> bool:
    """Call ``setup_tracing`` when ``ENABLE_TRACING`` is truthy.

    Safe to call once per process (bot subprocess). Returns whether OTEL was configured.
    """
    if not tracing_enabled_from_env():
        return False

    try:
        from pipecat.utils.tracing.setup import is_tracing_available, setup_tracing
    except ImportError as exc:
        _logger.warning(
            "ENABLE_TRACING is set but tracing utilities are unavailable: %s",
            exc,
        )
        return False

    if not is_tracing_available():
        _logger.warning("OpenTelemetry is not installed; install pipecat-ai[tracing]")
        return False

    try:
        exporter = _build_otlp_exporter()
    except ImportError as exc:
        _logger.warning("Could not load OTLP exporter (missing optional deps?): %s", exc)
        return False

    service_name = os.getenv("OTEL_SERVICE_NAME", "temple-cat-voice-bot").strip() or "temple-cat-voice-bot"
    console = _env_bool("OTEL_CONSOLE_EXPORT", False)

    ok = setup_tracing(
        service_name=service_name,
        exporter=exporter,
        console_export=console,
    )
    if ok:
        _logger.info(
            "OpenTelemetry tracing enabled service=%s endpoint=%s",
            service_name,
            os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        )
    else:
        _logger.warning("setup_tracing returned False; traces may not export")
    return ok
