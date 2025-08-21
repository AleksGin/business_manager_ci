from typing import (
    TYPE_CHECKING,
    List,
)
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from src.core.models.base import Base

if TYPE_CHECKING:
    from meetings.models import Meeting
    from tasks.models import Task
    from users.models import User


class Team(Base):
    __table_args__ = {"extend_existing": True}
    
    name: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
    )
    description: Mapped[str] = mapped_column(nullable=False)
    owner_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("users.uuid"),
        nullable=False,
    )
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_uuid],
        back_populates="owned_teams",
    )
    members: Mapped[List["User"]] = relationship(
        "User",
        foreign_keys="User.team_uuid",
        back_populates="team",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="team",
    )
    meetings: Mapped[List["Meeting"]] = relationship(
        "Meeting",
        back_populates="team",
    )
