from datetime import datetime
from typing import (
    TYPE_CHECKING,
    List,
)
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from core.models.associations import meeting_participants
from core.models.base import Base

if TYPE_CHECKING:
    from teams.models import Team
    from users.models import User


class Meeting(Base):
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
