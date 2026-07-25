from __future__ import annotations

from lychd.system import constants
from lychd.system.attribute_docs import path_attribute_summaries
from lychd.system.constants import (
    HOST_LAYOUT,
    PATH_LIFECYCLE_RECEIPT,
    PATH_LYCHD_TOML,
    PATH_POSTGRES_INIT_SCRIPT,
    PATH_REACTOR_INBOX_DIR,
    PATH_REACTOR_JOURNAL_DIR,
    PATH_XDG_CACHE_HOME,
    PATH_XDG_CONFIG_HOME,
    PATH_XDG_DATA_HOME,
)


def test_initialized_paths_reuse_their_adjacent_attribute_docstrings() -> None:
    required = {
        *HOST_LAYOUT,
        PATH_XDG_CACHE_HOME,
        PATH_XDG_CONFIG_HOME,
        PATH_XDG_DATA_HOME,
        PATH_LIFECYCLE_RECEIPT,
        PATH_LYCHD_TOML,
        PATH_POSTGRES_INIT_SCRIPT,
        PATH_REACTOR_INBOX_DIR,
        PATH_REACTOR_JOURNAL_DIR,
    }
    descriptions = path_attribute_summaries(constants)

    assert required <= descriptions.keys()
    assert all(descriptions[path].strip() for path in required)
    assert descriptions[PATH_POSTGRES_INIT_SCRIPT] == (
        "PostgreSQL bootstrap enabling pgvector and the current Phoenix compatibility database."
    )
    assert all("\n" not in description for description in descriptions.values())
