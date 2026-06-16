"""ORM models package.

Import every model module here so that `Base.metadata` is fully populated when
Alembic (and the app) import this package. No models exist yet — the User and
CorrectionHistory models land in later milestones (PROGRESS.md items 2 and 4).
"""

from backend.app.database import Base  # re-exported for convenience

__all__ = ["Base"]
