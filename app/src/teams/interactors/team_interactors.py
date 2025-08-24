from typing import (
    List,
    Optional,
)
from uuid import UUID

from src.core.interfaces import (
    DBSession,
    PermissionValidator,
    UUIDGenerator,
)
from src.teams.interfaces import (
    TeamRepository,
)
from src.teams.models import Team
from src.teams.schemas.team import TeamUpdate
from src.users.interfaces import UserRepository
from src.users.models import RoleEnum


class CreateTeamDTO:
    """DTO для создания команды"""

    def __init__(
        self,
        name: str,
        description: str,
        owner_uuid: UUID,
    ) -> None:
        self.name = name
        self.description = description
        self.owner_uuid = owner_uuid


class CreateTeamInteractor:
    """Интерактор для создания команды"""

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        uuid_generator: UUIDGenerator,
        db_session: DBSession,
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._uuid_generator = uuid_generator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        dto: CreateTeamDTO,
    ) -> Team:
        """Создать новую команду"""

        try:
            # 1. Найти актора
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            if not actor:
                raise ValueError("Пользователь не найден")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_create_team(actor):
                    raise PermissionError("Нет прав для создания команды")
            else:
                # Временная простая проверка
                if actor.role == RoleEnum.EMPLOYEE:
                    raise PermissionError("Сотрудники не могут создавать команды")

            # 3. Бизнес-валидация
            if await self._team_repo.exists_by_name(dto.name):
                raise ValueError(f"Команда с названием '{dto.name}' уже существует")

            # Проверить что владелец существует
            owner = await self._user_repo.get_by_uuid(dto.owner_uuid)
            if not owner:
                raise ValueError("Владелец команды не найден")

            # 4. Создать команду
            team_uuid = self._uuid_generator()

            team = Team(
                uuid=team_uuid,
                name=dto.name,
                description=dto.description,
                owner_uuid=dto.owner_uuid,
            )

            # 5. Сохранить
            created_team = await self._team_repo.create_team(team)
            await self._db_session.flush()

            # 6. Добавить владельца в команду
            owner.team_uuid = created_team.uuid
            await self._user_repo.update_user(owner)

            await self._db_session.commit()
            return created_team

        except Exception:
            await self._db_session.rollback()
            raise


class GetTeamInteractor:
    """Интерактор для получения команды"""

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def get_by_uuid(
        self,
        actor_uuid: UUID,
        team_uuid: UUID,
        with_members: bool = False,
    ) -> Optional[Team]:
        """Получить команду по UUID"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Получить команду
        if with_members:
            team = await self._team_repo.get_team_with_members(team_uuid)
        else:
            team = await self._team_repo.get_by_uuid(team_uuid)

        if not team:
            return None

        # 3. Проверить права доступа
        if self._permission_validator:
            if not await self._permission_validator.can_view_team(actor, team):
                raise PermissionError("Нет прав для просмотра команды")
        else:
            # Временная простая проверка
            is_owner = team.owner_uuid == actor.uuid
            is_member = actor.team_uuid == team.uuid
            is_admin = actor.role == RoleEnum.ADMIN

            if not (is_owner or is_member or is_admin):
                raise PermissionError("Нет прав для просмотра команды")

        return team


class UpdateTeamInteractor:
    """Интерактор для обновления команды"""

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        team_uuid: UUID,
        update_data: TeamUpdate,
    ) -> Team:
        """Обновить команду"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            team = await self._team_repo.get_by_uuid(team_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not team:
                raise ValueError("Команда не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_update_team(actor, team):
                    raise PermissionError("Нет прав для обновления команды")
            else:
                # Временная простая проверка
                is_owner = team.owner_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_owner or is_admin):
                    raise PermissionError(
                        "Только владелец или админ может обновлять команду"
                    )

            # 3. Валидация изменений
            if update_data.name is not None:
                # Проверить уникальность нового названия
                if update_data.name != team.name:
                    if await self._team_repo.exists_by_name(update_data.name):
                        raise ValueError(
                            f"Команда с названием '{update_data.name}' уже существует"
                        )
                team.name = update_data.name

            if update_data.description is not None:
                team.description = update_data.description

            # 4. Сохранить
            updated_team = await self._team_repo.update_team(team)
            await self._db_session.commit()
            return updated_team

        except Exception:
            await self._db_session.rollback()
            raise


class DeleteTeamInteractor:
    """Интерактор для удаления команды"""

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        team_uuid: UUID,
    ) -> bool:
        """Удалить команду"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            team = await self._team_repo.get_by_uuid(team_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not team:
                raise ValueError("Команда не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_delete_team(actor, team):
                    raise PermissionError("Нет прав для удаления команды")
            else:
                # Временная простая проверка
                is_owner = team.owner_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_owner or is_admin):
                    raise PermissionError(
                        "Только владелец или админ может удалять команду"
                    )

            # 3. Удалить команду (участники автоматически покинут команду через SET NULL)
            result = await self._team_repo.delete_team(team_uuid)
            if result:
                await self._db_session.commit()
            return result

        except Exception:
            await self._db_session.rollback()
            raise


class QueryTeamsInteractor:
    """Интерактор для получения списка команд"""

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
        owner_uuid: Optional[UUID] = None,
        search_query: Optional[str] = None,
    ) -> List[Team]:
        """Получить список команд"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить права доступа
        if actor.role == RoleEnum.EMPLOYEE:
            # Сотрудники видят только свою команду
            if actor.team_uuid:
                team = await self._team_repo.get_by_uuid(actor.team_uuid)
                return [team] if team else []
            else:
                return []

        # Админы и менеджеры видят все команды

        if search_query:
            # 3. Поиск команд
            teams = await self._team_repo.search_teams(
                query=search_query,
                limit=limit,
            )
        else:
            # 3. Получить список команд
            teams = await self._team_repo.list_teams(
                limit=limit,
                offset=offset,
                owner_uuid=owner_uuid,
            )

        return teams
