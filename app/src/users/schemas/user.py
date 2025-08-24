from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)

from src.users.models.user import (
    GenderEnum,
    RoleEnum,
)


class UserBase(BaseModel):
    email: EmailStr = Field(
        description="Email пользователя",
        examples=["user@example.ru"],
    )
    name: str = Field(
        min_length=1,
        max_length=50,
        description="Имя пользователя",
    )
    surname: str = Field(
        min_length=1,
        max_length=50,
        description="Фамилия пользователя",
    )
    gender: GenderEnum = Field(description="Пол пользователя")
    birth_date: date = Field(
        description="Дата рождения",
        examples=["1994-08-08"],
    )


class UserCreate(UserBase):
    password: str = Field(
        min_length=10,
        max_length=80,
        description="Пароль (минимум 10 символов)",
    )


class UserResponse(UserBase):
    uuid: UUID
    is_active: bool
    is_verified: bool
    role: Optional[RoleEnum] = None
    team_uuid: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class UserInTeam(BaseModel):
    uuid: UUID
    name: str
    surname: str
    email: EmailStr
    role: Optional[RoleEnum] = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr = Field(description="Введите Email для входа")
    password: str = Field(description="Пароль")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
    )
    surname: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
    )
    gender: Optional[GenderEnum] = None
    birth_date: Optional[date] = None
    role: Optional[RoleEnum] = None
    team_uuid: Optional[UUID] = None


class UserTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserChangePassword(BaseModel):
    current_password: str = Field(description="Текущий пароль")
    new_password: str = Field(
        min_length=10,
        max_length=80,
        description="Новый пароль (минимум 10 символов)",
    )


class UserAssignRole(BaseModel):
    role: RoleEnum = Field(description="Назначаемая роль")


class UserJoinTeam(BaseModel):
    invite_code: str = Field(
        min_length=6,
        max_length=50,
        description="Код приглашения в команду",
    )
