import logging

import pytest

from lychd.config.logging import apply_logging

# 1. Silence the noisy libs using standard logging
logging.getLogger("faker").setLevel(logging.WARNING)


@pytest.fixture(autouse=True, scope="session")
def setup_test_logging() -> None:
    """Configure test logging once through the shared runtime logging module."""
    apply_logging(force_json=False)
