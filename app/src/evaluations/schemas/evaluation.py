from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from evaluations.models.evaluation import ScoresEnum
from users.schemas import UserInTeam


class EvaluationBase(BaseModel):
    score: ScoresEnum = Field(description="Оценка выполнения задачи")
    comment: Optional[str] = Field(
        None,
        max_length=200,
        description="Комментарий к оценке",
        examples=["Отличная работа, задача выполнена в срок"],
    )


class EvaluationCreate(EvaluationBase):
    task_uuid: UUID = Field(description="UUID оцениваемой задачи")
    evaluated_user_uuid: UUID = Field(description="UUID оцениваемого пользователя")


class EvaluationResponse(EvaluationBase):
    uuid: UUID
    task_uuid: UUID
    evaluator_uuid: Optional[UUID] = None
    evaluated_user_uuid: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationWithDetails(EvaluationResponse):
    evaluator: Optional[UserInTeam] = None
    evaluated_user: Optional[UserInTeam] = None


class EvaluationUpdate(BaseModel):
    score: Optional[ScoresEnum] = Field(
        None,
        description="Оценка",
    )
    comment: Optional[str] = Field(
        None,
        max_length=200,
        description="Комментарий к оценке",
    )


class EvaluationFilter(BaseModel):
    task_uuid: Optional[UUID] = Field(
        None,
        description="UUID задачи",
    )
    score: Optional[ScoresEnum] = Field(
        None,
        description="Оценка",
    )
    evaluator_uuid: Optional[UUID] = Field(
        None,
        description="UUID оценивающего",
    )
    evaluated_user_uuid: Optional[UUID] = Field(
        None,
        description="UUID оцениваемого пользователя",
    )


class UserEvaluationStats(BaseModel):
    user_uuid: UUID
    total_evaluations: int = Field(description="Общее количество оценок")
    average_score: float = Field(description="Средняя оценка")
    score_distribution: dict[ScoresEnum, int] = Field(
        default_factory=dict,
        description="Распределение оценок по типам",
    )

    model_config = ConfigDict(from_attributes=True)
