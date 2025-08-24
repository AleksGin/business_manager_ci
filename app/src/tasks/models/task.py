import enum as PyEnum
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Optional,
)
from uuid import UUID

from sqlalchemy import (
    Enum,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from src.core.models.base import Base

if TYPE_CHECKING:
    from src.evaluations.models import Evaluation
    from src.teams.models import Team
    from src.users.models import User


class StatusEnum(PyEnum.Enum):
    OPENED = "Open"
    IN_PROGRESS = "In progress"
    DONE = "Done"


class Task(Base):
    __table_args__ = {"extend_existing": True}
    
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    deadline: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum),
        nullable=False,
        default=StatusEnum.OPENED,
    )
    assignee_uuid: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(
            "users.uuid",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    team_uuid: Mapped[UUID] = mapped_column(
        ForeignKey(
            "teams.uuid",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    creator_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("users.uuid"),
        nullable=False,
    )
    assignee: Mapped["User"] = relationship(
        "User",
        foreign_keys=[assignee_uuid],
        back_populates="assigned_tasks",
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_uuid],
        back_populates="created_tasks",
    )
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="tasks",
    )
    evaluation: Mapped["Evaluation"] = relationship(
        "Evaluation", foreign_keys="Evaluation.task_uuid", back_populates="task"
    )
