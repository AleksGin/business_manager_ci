from datetime import datetime
from typing import (
    TYPE_CHECKING,
    List,
)
from uuid import UUID

from src.core.models.associations import meeting_participants
from src.core.models.base import Base
from sqlalchemy import (
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from src.teams.models import Team
    from src.users.models import User


class Meeting(Base):
    __table_args__ = {"extend_existing": True}
    
    title: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        String(240),
        nullable=True,
    )
    date_time: Mapped[datetime] = mapped_column(nullable=False)
    creator_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("users.uuid"),
        nullable=False,
    )
    team_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("teams.uuid"),
        nullable=False,
    )
    participants: Mapped[List["User"]] = relationship(
        "User",
        secondary=meeting_participants,
        back_populates="meetings",
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_uuid],
        back_populates="created_meetings",
    )
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="meetings",
    )
