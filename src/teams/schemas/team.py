from typing import (
    List,
    Optional,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from users.schemas import UserInTeam


class TeamBase(BaseModel):
    name: str = Field(
        min_length=5,
        max_length=150,
        examples=["Название команды"],
    )
    description: str = Field(
        min_length=10,
        max_length=350,
        examples=["Описание команды"],
    )


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    uuid: UUID
    owner_uuid: UUID

    model_config = ConfigDict(from_attributes=True)


class TeamWithMembers(TeamResponse):
    members: List[UserInTeam] = Field(default_factory=list)


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(
        min_length=5,
        max_length=150,
        description="Название команды",
    )
    description: Optional[str] = Field(
        min_length=10,
        max_length=350,
        description="Описание команды",
    )


class TeamInvite(BaseModel):
    user_uuid: Optional[UUID] = Field(
        None,
        description="UUID пользователя для приглашения",
    )
    user_email: Optional[EmailStr] = Field(
        None,
        description="email пользователя для приглашения",
        examples=["user@example.com"],
    )

    @model_validator(mode="after")
    def validate_one_identifier(self) -> "TeamInvite":
        if not self.user_uuid and not self.user_email:
            raise ValueError("Необходимо ввести почту пользователя ИЛИ uuid")
        return self


class TeamRemoveMember(BaseModel):
    user_uuid: UUID = Field(description="UUID пользователя для удаления")


class TeamTransferOwnership(BaseModel):
    new_owner_uuid: UUID = Field(description="UUID нового владельца команды")

class TeamInviteResponse(BaseModel):
    message: str
    invite_code: str
    expires_in_hours: int