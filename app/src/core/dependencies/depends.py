from core.interfaces.permissions import PermissionValidator
from core.providers.permission_validator_provider import PermissionValidatorProvider

from typing import (
    Annotated,
    AsyncGenerator,
)
from uuid import UUID

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.interfaces import (
    TokenRepository,
    UUIDGenerator,
)
from core.models.db_helper import db_helper
from core.providers.jwt_provider import jwt_provider
from core.providers.token_provider import TokenRepositoryProvider
from core.providers.uuid_generator_provider import UUIDGeneratorProvider
from evaluations.crud import EvaluationCRUD
from evaluations.interfaces import EvaluationRepository
from meetings.crud import MeetingCRUD
from meetings.interfaces import MeetingRepository
from tasks.crud import TaskCRUD
from tasks.interfaces import TaskRepository
from teams.crud import TeamCRUD
from teams.interfaces import (
    TeamMembershipManager,
    TeamRepository,
)
from teams.providers import TeamMembershipManagerProvider
from users.crud import UserCRUD
from users.interfaces import (
    PasswordHasher,
    UserActivationManager,
    UserRepository,
    UserValidator,
)
from users.models import User
from users.providers import (
    BcryptPasswordHasherProvider,
    UserActivationManagerProvider,
    UserValidatorProvider,
)

security = HTTPBearer()

# === Базовые зависимости ===


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Получить сессию из БД"""
    async for session in db_helper.session_getter():
        yield session


def get_uuid_generator() -> UUIDGenerator:
    """Получить генератор UUID"""
    return UUIDGeneratorProvider()


def get_password_hasher() -> PasswordHasher:
    """Получить хешер паролей"""
    return BcryptPasswordHasherProvider()


# === Зависимости репозиториев ===


def get_user_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> UserRepository:
    """Получить репозиторий пользователей"""
    return UserCRUD(session)


def get_token_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> TokenRepository:
    """Получить репозиторий токенов"""
    return TokenRepositoryProvider(session)


# === Зависимости провайдеров ===


def get_user_validator(
    user_repo: Annotated[
        UserRepository,
        Depends(get_user_repository),
    ],
) -> UserValidator:
    """Получить валидатор пользователей"""
    return UserValidatorProvider(user_repo)


def get_user_activation_manager(
    user_repo: Annotated[
        UserRepository,
        Depends(get_user_repository),
    ],
    token_repo: Annotated[
        TokenRepository,
        Depends(get_token_repository),
    ],
    password_hasher: Annotated[
        PasswordHasher,
        Depends(get_password_hasher),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
    user_validator: Annotated[
        UserValidator,
        Depends(get_user_validator),
    ],
) -> UserActivationManager:
    """Получить менеджер активации пользователей"""
    return UserActivationManagerProvider(
        user_repo=user_repo,
        jwt_provider=jwt_provider,
        token_repository=token_repo,
        password_hasher=password_hasher,
        db_session=session,
        user_validator=user_validator,
    )


# === Аутентификация ===


async def get_current_user_uuid(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(security),
    ],
) -> str:
    """Получить UUID текущего пользователя из JWT токена"""

    token = credentials.credentials

    user_uuid = jwt_provider.get_user_from_token(token)
    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    return str(user_uuid)


async def get_current_user(
    user_uuid: Annotated[
        str,
        Depends(get_current_user_uuid),
    ],
    user_repo: Annotated[
        UserRepository,
        Depends(get_user_repository),
    ],
) -> User:
    """Получить текущего пользователя"""

    user = await user_repo.get_by_uuid(UUID(user_uuid))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:
    """Получить текущего активного пользователя"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт не найден",
        )

    return current_user


# === Типы для аннотаций ===

SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
TokenRepoDep = Annotated[TokenRepository, Depends(get_token_repository)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
UserValidatorDep = Annotated[UserValidator, Depends(get_user_validator)]
UserActivationDep = Annotated[
    UserActivationManager, Depends(get_user_activation_manager)
]
UUIDGeneratorDep = Annotated[UUIDGenerator, Depends(get_uuid_generator)]
CurrentUserDep = Annotated[User, Depends(get_current_active_user)]


# === Зависимости репозиториев Teams ===


def get_team_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> TeamRepository:
    """Получить репозиторий команд"""
    return TeamCRUD(session)


# === Зависимости провайдеров Teams ===


def get_team_membership_manager(
    team_repo: Annotated[
        TeamRepository,
        Depends(get_team_repository),
    ],
    user_repo: Annotated[
        UserRepository,
        Depends(get_user_repository),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> TeamMembershipManager:
    """Получить менеджер управления участниками команд"""
    return TeamMembershipManagerProvider(
        team_repo=team_repo,
        user_repo=user_repo,
        db_session=session,
    )


# === Типы для аннотаций Teams ===

TeamRepoDep = Annotated[TeamRepository, Depends(get_team_repository)]
TeamMembershipDep = Annotated[
    TeamMembershipManager,
    Depends(get_team_membership_manager),
]


# === Зависимости репозиториев Tasks ===


def get_task_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> TaskRepository:
    """Получить репозиторий задач"""
    return TaskCRUD(session)


# === Типы для аннотаций Tasks ===

TaskRepoDep = Annotated[TaskRepository, Depends(get_task_repository)]


# === Зависимости репозиториев Evaluations ===


def get_evaluation_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> EvaluationRepository:
    """Получить репозиторий оценок"""
    return EvaluationCRUD(session)


# === Типы для аннотаций Evaluations ===

EvaluationRepoDep = Annotated[EvaluationRepository, Depends(get_evaluation_repository)]


# === Зависимости репозиториев Meetings ===


def get_meeting_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> MeetingRepository:
    """Получить репозиторий встреч"""
    return MeetingCRUD(session)


# === Типы для аннотаций Meetings ===

MeetingRepoDep = Annotated[MeetingRepository, Depends(get_meeting_repository)]


def get_permission_validator() -> PermissionValidator:
    """Получить валидатор прав доступа"""
    return PermissionValidatorProvider()


PermissionValidatorDep = Annotated[
    PermissionValidator,
    Depends(get_permission_validator),
]
