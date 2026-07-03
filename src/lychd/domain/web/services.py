"""Web persistence services (conversation sessions)."""

from __future__ import annotations

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from lychd.db.models import Session


class SessionService(SQLAlchemyAsyncRepositoryService[Session]):
    """CRUD service for Bridge/API conversation ``Session`` rows."""

    class Repository(SQLAlchemyAsyncRepository[Session]):
        model_type = Session

    repository_type = Repository
