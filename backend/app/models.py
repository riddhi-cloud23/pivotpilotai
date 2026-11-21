from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from backend.app.db import Base

JSON_DOCUMENT = MutableDict.as_mutable(JSON().with_variant(JSONB, "postgresql"))


class UserWorkspace(Base):
    __tablename__ = "user_workspaces"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
