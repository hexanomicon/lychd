import pytest
import structlog


@pytest.fixture(autouse=True, scope="session")
def setup_test_logging() -> None:
    # 2. Tell structlog to pipe everything into the standard library - configure logs for CLI
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
