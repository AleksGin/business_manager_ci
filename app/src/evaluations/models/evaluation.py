import enum as PyEnum
from typing import (
    TYPE_CHECKING,
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
    from tasks.models import Task
    from users.models import User


class ScoresEnum(PyEnum.Enum):
    UNACCEPTABLE = "Unacceptable"
    BAD = "Bad"
    SATISFACTORY = "Satisfactory"
    GOOD = "Good"
    GREAT = "Great"


class Evaluation(Base):
    __table_args__ = {"extend_existing": True}
    
    task_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.uuid", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    evaluator_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    evaluated_user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    score: Mapped[ScoresEnum] = mapped_column(
        Enum(ScoresEnum),
        nullable=False,
    )
    comment: Mapped[str] = mapped_column(String(200), nullable=True)
    evaluator: Mapped["User"] = relationship(
        "User", foreign_keys=[evaluator_uuid], back_populates="given_evaluations"
    )
    evaluated_user: Mapped["User"] = relationship(
        "User", foreign_keys=[evaluated_user_uuid], back_populates="evaluations"
    )
    task: Mapped["Task"] = relationship(
        "Task", foreign_keys=[task_uuid], back_populates="evaluation"
    )
