from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from src.tasks.models.task import StatusEnum
from src.users.schemas import UserInTeam


class TaskBase(BaseModel):
    __table_args__ = {"extend_existing": True}
    
    title: str = Field(
        min_length=3,
        max_length=80,
        description="Название задачи",
        examples=["Реализовать API пользователей"],
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Описание задачи",
        examples=["Создать CRUD операции для работы с пользователем"],
    )
    deadline: datetime = Field(
        description="Дедлайн выполнения задачи",
        examples=["2024-12-31T23:59:59"],
    )


class TaskCreate(TaskBase):
    team_uuid: UUID = Field(description="UUID команды")
    assignee_uuid: Optional[UUID] = Field(
        None, description="UUID исполнителя (опционально)"
    )


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=80,
        description="Название задачи",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Описание задачи",
    )
    deadline: Optional[datetime] = Field(
        None,
        description="Дедлайн выполнения задачи",
    )
    team_uuid: Optional[UUID] = Field(
        None,
        description="UUID команды",
    )
    status: Optional[StatusEnum] = Field(
        None,
        description="Статус задачи",
    )
    assignee_uuid: Optional[UUID] = Field(
        None,
        description="UUID исполнителя",
    )


class TaskResponse(TaskBase):
    uuid: UUID
    status: StatusEnum
    assignee_uuid: Optional[UUID] = None
    team_uuid: UUID
    creator_uuid: UUID

    model_config = ConfigDict(from_attributes=True)


class TaskWithDetails(TaskResponse):
    assignee: Optional[UserInTeam] = None
    creator: UserInTeam


class TaskAssign(BaseModel):
    assignee_uuid: UUID = Field(description="UUID нового исполнителя")


class TaskStatusUpdate(BaseModel):
    status: StatusEnum = Field(description="Новый статус задачи")


class TaskFilter(BaseModel):
    status: Optional[StatusEnum] = Field(
        None,
        description="Статус задачи",
    )
    team_uuid: Optional[UUID] = Field(
        None,
        description="UUID команды",
    )
    creator_uuid: Optional[UUID] = Field(
        None,
        description="UUID создателя задачи",
    )
    assignee_uuid: Optional[UUID] = Field(
        None,
        description="UUID исполнителя задачи",
    )

