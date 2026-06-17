"""ORM models package.

Import every model module here so that `Base.metadata` is fully populated when
Alembic (and the app) import this package.
"""

from backend.app.database import Base  # re-exported for convenience
from backend.app.models.user import User  # noqa: F401 — registers table with Base.metadata
from backend.app.models.history import CorrectionHistory  # noqa: F401

__all__ = ["Base", "User", "CorrectionHistory"]
