from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from users.schemas import UserInTeam


class MeetingBase(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=120,
        description="Название встречи",
        examples=["Планирование спринта"],
    )
    description: str = Field(
        min_length=3,
        max_length=450,
        description="Описание встречи",
        examples=["Обсуждение задач на следующую неделю"],
    )
    date_time: datetime = Field(
        description="Дата и время встречи",
        examples=["2024-12-25T14:00:00"],
    )


class MeetingCreate(MeetingBase):
    team_uuid: UUID = Field(description="UUID команды")
    participants_uuids: List[UUID] = Field(
        default_factory=list,
        description="Список UUID участников встречи",
    )

    @model_validator(mode="after")
    def validate_future_data(self) -> "MeetingCreate":
        if self.date_time <= datetime.now():
            raise ValueError("Дата встречи должна быть в будущем")
        return self


class MeetingResponse(MeetingBase):
    uuid: UUID
    creator_uuid: UUID
    team_uuid: UUID

    model_config = ConfigDict(from_attributes=True)


class MeetingWithDetails(MeetingResponse):
    creator: UserInTeam
    participants: List[UserInTeam] = Field(default_factory=list)


class MeetingAddParticipants(BaseModel):
    participants_uuids: List[UUID] = Field(
        description="Спиок UUID участников для добавления",
    )


class MeetingRemoveParticipants(BaseModel):
    participants_uuids: List[UUID] = Field(
        description="Спиок UUID участников для удаления",
    )


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=120,
        description="Название встречи",
    )
    description: Optional[str] = Field(
        None,
        min_length=3,
        max_length=240,
        description="Описание встречи",
    )
    date_time: Optional[datetime] = Field(
        None,
        description="Дата и время встречи",
    )

    @model_validator(mode="after")
    def validate_future_data(self) -> "MeetingUpdate":
        if self.date_time and self.date_time <= datetime.now():
            raise ValueError("Дата встречи должна быть в будущем")
        return self


class MeetingFilter(BaseModel):
    team_uuid: Optional[UUID] = Field(
        None,
        description="UUID команды",
    )
    participant_uuid: Optional[UUID] = Field(
        None,
        description="UUID участника встречи",
    )
    creator_uuid: Optional[UUID] = Field(
        None,
        description="UUID создателя встречи",
    )
    date_from: Optional[datetime] = Field(
        None,
        description="Начальная дата встречи",
    )
    date_to: Optional[datetime] = Field(
        None,
        description="Конечная дата встречи",
    )
