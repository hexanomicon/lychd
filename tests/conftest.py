import logging
from collections.abc import Iterator

import pytest
import structlog

from lychd.config.logging import apply_logging

# 1. Silence the noisy libs using standard logging
logging.getLogger("faker").setLevel(logging.WARNING)


@pytest.fixture(autouse=True)
def setup_test_logging() -> Iterator[None]:
    """Configure logging per test through the shared runtime logging module.

    Function-scoped and reset on both ends: structlog caches its bound logger on
    first use, so if the first log emission happens while a ``CliRunner`` or
    ``capsys`` has swapped in a transient stdout/stderr, that soon-closed stream
    would be cached process-wide and every later test logging through the runes
    loader would raise ``ValueError: I/O operation on closed file``. Resetting
    around each test keeps the global structlog state from leaking a dead handle.
    """
    structlog.reset_defaults()
    apply_logging(force_json=False)
    # Litestar's StructLoggingConfig enables ``cache_logger_on_first_use``, which
    # monkeypatches each lazy proxy's ``bind`` to a logger holding whatever stdout
    # was live at first emission. Under ``CliRunner``/``capsys`` that stream is
    # transient and soon closed, so ``reset_defaults`` alone can't undo the patch
    # and every later test logging through the runes loader raises
    # ``ValueError: I/O operation on closed file``. Disabling the cache in tests
    # makes each emission re-resolve the live stream.
    structlog.configure(cache_logger_on_first_use=False)
    yield
    structlog.reset_defaults()
