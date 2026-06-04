from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import LogFormat, settings


def add_app_context(
    logger: logging.Logger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject application-level context into every log entry."""
    event_dict["app"] = settings.APP_NAME
    event_dict["env"] = settings.APP_ENV.value
    event_dict["version"] = settings.APP_VERSION
    return event_dict


def drop_color_message_key(
    logger: logging.Logger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Drop uvicorn color_message key — we don't need ANSI in JSON logs."""
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging() -> None:
    """Configure structlog for the application.

    In development: pretty console output with colors.
    In production: structured JSON output.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
        drop_color_message_key,
    ]

    if settings.LOG_FORMAT == LogFormat.CONSOLE:
        # ── Development: pretty console ──────────────────────────────────
        structlog.configure(
            processors=shared_processors
            + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=settings.LOG_LEVEL,
        )
    else:
        # ── Production: JSON output ───────────────────────────────────────
        structlog.configure(
            processors=shared_processors
            + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(settings.LOG_LEVEL)

    # Silence noisy third-party loggers
    for noisy_logger in ("uvicorn.access", "sqlalchemy.engine", "asyncio"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    if settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
