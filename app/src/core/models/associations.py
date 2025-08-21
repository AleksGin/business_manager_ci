from sqlalchemy import (
    Column,
    ForeignKey,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID

from src.core.models.base import Base

meeting_participants = Table(
    "meeting_participants",
    Base.metadata,
    Column("meeting_uuid", UUID(as_uuid=True), ForeignKey("meetings.uuid")),
    Column("user_uuid", UUID(as_uuid=True), ForeignKey("users.uuid")),
    extend_existing=True,
)
