import enum as PyEnum
from datetime import date
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)
from uuid import UUID

from sqlalchemy import (
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from core.models.associations import meeting_participants
from core.models.base import Base


class RoleEnum(PyEnum.Enum):
    EMPLOYEE = "Employee"
    MANAGER = "Manager"
    ADMIN = "Administrator"


class GenderEnum(PyEnum.Enum):
    MALE = "Man"
    FEMALE = "Woman"


if TYPE_CHECKING:
    from evaluations.models import Evaluation
    from meetings.models import Meeting
    from tasks.models import Task
    from teams.models import Team
    from core.models import UserToken


class User(Base):
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

    name: Mapped[str] = mapped_column(nullable=False)
    surname: Mapped[str] = mapped_column(nullable=False)
    gender: Mapped[GenderEnum] = mapped_column(
        Enum(GenderEnum),
        nullable=False,
    )
    birth_date: Mapped[date] = mapped_column(nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum),
        nullable=True,
    )
    team_uuid: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(
            "teams.uuid",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[team_uuid],
        back_populates="members",
    )
    owned_teams: Mapped[List["Team"]] = relationship(
        "Team",
        foreign_keys="Team.owner_uuid",
        back_populates="owner",
    )
    created_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.creator_uuid",
        back_populates="creator",
    )
    assigned_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.assignee_uuid",
        back_populates="assignee",
    )
    meetings: Mapped[List["Meeting"]] = relationship(
        "Meeting",
        secondary=meeting_participants,
        back_populates="participants",
    )
    created_meetings: Mapped[List["Meeting"]] = relationship(
        "Meeting", foreign_keys="Meeting.creator_uuid", back_populates="creator"
    )
    given_evaluations: Mapped[List["Evaluation"]] = relationship(
        "Evaluation",
        foreign_keys="Evaluation.evaluator_uuid",
        back_populates="evaluator",
    )
    evaluations: Mapped[List["Evaluation"]] = relationship(
        "Evaluation",
        foreign_keys="Evaluation.evaluated_user_uuid",
        back_populates="evaluated_user",
    )
    tokens: Mapped[List["UserToken"]] = relationship(
        "UserToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
