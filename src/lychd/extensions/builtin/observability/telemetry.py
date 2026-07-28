"""Dormant Phoenix export adapter; not native Oculus.

The application does not compose this plugin today. Any future activation requires the bounded
allowlist and privacy contract owned by ADR 29.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import logfire
from litestar.plugins import InitPluginProtocol
from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
from logfire import ConsoleOptions
from opentelemetry import trace

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class TelemetryPlugin(InitPluginProtocol):
    """Configure the legacy Logfire/OTel export path to an external Phoenix Eye."""

    def __init__(self, otel_endpoint: str) -> None:
        """Initialize the telemetry plugin.

        Args:
            otel_endpoint (str): The endpoint where to send the tracing data

        """
        self.otel_endpoint = otel_endpoint

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        # 1. Force Logfire/OTel to send data to your local Phoenix instance
        #    instead of the Logfire Cloud.
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = self.otel_endpoint

        # 2. Configure Logfire
        #    - send_to_logfire=False: Don't try to auth with Pydantic.
        #    - console: specific settings for local dev output.
        logfire.configure(send_to_logfire=False, console=ConsoleOptions(min_log_level="debug", colors="always"))

        # 3. Instrument Libraries
        #    This catches PydanticAI activity and HTTP transport metadata. Generic
        #    HTTP bodies and headers may contain prompts or bearer credentials and
        #    are never captured wholesale.
        logfire.instrument_pydantic_ai()
        logfire.instrument_httpx(
            capture_all=False,
            capture_headers=False,
            capture_request_body=False,
            capture_response_body=False,
        )

        # 4. Instrument Litestar
        #    Logfire has already initialized the Global Tracer Provider.
        #    We explicitly tell Litestar to use that existing provider
        #    so we don't end up with two separate tracing systems.
        otel_config = OpenTelemetryConfig(tracer_provider=trace.get_tracer_provider())

        app_config.plugins.append(OpenTelemetryPlugin(config=otel_config))

        return app_config
