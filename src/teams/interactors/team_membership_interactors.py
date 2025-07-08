import secrets
from datetime import datetime, timedelta
from typing import (
    Dict,
    List,
    Optional,
)
from uuid import UUID

from core.interfaces import (
    DBSession,
    PermissionValidator,
)
from teams.interfaces import (
    TeamRepository,
)
from teams.models import Team
from users.interfaces import UserRepository
from users.models import RoleEnum, User


class AddTeamMemberInteractor:
    """Интерактор для добавления участника в команду"""

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
        user_uuid: UUID,
    ) -> bool:
        """Добавить участника в команду"""

        try:
            # 1. Найти всех участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            team = await self._team_repo.get_by_uuid(team_uuid)
            new_member = await self._user_repo.get_by_uuid(user_uuid)

            if not actor:
                raise ValueError("Пользователь-инициатор не найден")
            if not team:
                raise ValueError("Команда не найдена")
            if not new_member:
                raise ValueError("Добавляемый пользователь не найден")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_add_team_member(
                    actor, team
                ):
                    raise PermissionError("Нет прав для добавления участников")
            else:
                # Временная простая проверка
                is_owner = team.owner_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN
                is_manager_same_team = (
                    actor.role == RoleEnum.MANAGER and actor.team_uuid == team.uuid
                )

                if not (is_owner or is_admin or is_manager_same_team):
                    raise PermissionError(
                        "Только владелец команды, админ или менеджер команды может добавлять участников"
                    )

            # 3. Бизнес-валидация
            if new_member.team_uuid is not None:
                if new_member.team_uuid == team.uuid:
                    raise ValueError("Пользователь уже состоит в этой команде")
                else:
                    raise ValueError("Пользователь уже состоит в другой команде")

            if not new_member.is_active:
                raise ValueError("Нельзя добавить неактивного пользователя")

            # 4. Добавить в команду
            new_member.team_uuid = team.uuid
            await self._user_repo.update_user(new_member)
            await self._db_session.commit()

            return True

        except Exception:
            await self._db_session.rollback()
            raise


class RemoveTeamMemberInteractor:
    """Интерактор для удаления участника из команды"""

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
        user_uuid: UUID,
    ) -> bool:
        """Удалить участника из команды"""

        try:
            # 1. Найти всех участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            team = await self._team_repo.get_by_uuid(team_uuid)
            member = await self._user_repo.get_by_uuid(user_uuid)

            if not actor:
                raise ValueError("Пользователь-инициатор не найден")
            if not team:
                raise ValueError("Команда не найдена")
            if not member:
                raise ValueError("Удаляемый пользователь не найден")

            # 2. Проверить права доступа
            is_self_removal = actor.uuid == member.uuid

            if self._permission_validator:
                if not is_self_removal:
                    if not await self._permission_validator.can_remove_team_member(
                        actor, team
                    ):
                        raise PermissionError("Нет прав для удаления участников")
            else:
                # Временная простая проверка
                if not is_self_removal:
                    is_owner = team.owner_uuid == actor.uuid
                    is_admin = actor.role == RoleEnum.ADMIN
                    is_manager_same_team = (
                        actor.role == RoleEnum.MANAGER and actor.team_uuid == team.uuid
                    )

                    if not (is_owner or is_admin or is_manager_same_team):
                        raise PermissionError(
                            "Только владелец команды, админ или менеджер команды может удалять участников"
                        )

            # 3. Бизнес-валидация
            if member.team_uuid != team.uuid:
                raise ValueError("Пользователь не состоит в этой команде")

            # Нельзя удалить владельца команды
            if member.uuid == team.owner_uuid:
                if is_self_removal:
                    raise ValueError(
                        "Владелец не может покинуть команду. Сначала передайте владение другому участнику"
                    )
                else:
                    raise ValueError("Нельзя исключить владельца команды")

            # 4. Удалить из команды
            member.team_uuid = None
            await self._user_repo.update_user(member)
            await self._db_session.commit()

            return True

        except Exception:
            await self._db_session.rollback()
            raise


class TransferOwnershipInteractor:
    """Интерактор для передачи владения командой"""

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
        new_owner_uuid: UUID,
    ) -> bool:
        """Передать владение командой"""

        try:
            # 1. Найти всех участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            team = await self._team_repo.get_by_uuid(team_uuid)
            new_owner = await self._user_repo.get_by_uuid(new_owner_uuid)

            if not actor:
                raise ValueError("Пользователь-инициатор не найден")
            if not team:
                raise ValueError("Команда не найдена")
            if not new_owner:
                raise ValueError("Новый владелец не найден")

            # 2. Проверить права доступа
            if self._permission_validator:
                # TODO: Добавить метод can_transfer_ownership в PermissionValidator
                pass

            # Только текущий владелец или админ может передавать владение
            is_current_owner = team.owner_uuid == actor.uuid
            is_admin = actor.role == RoleEnum.ADMIN

            if not (is_current_owner or is_admin):
                raise PermissionError(
                    "Только текущий владелец или админ может передать владение"
                )

            # 3. Бизнес-валидация
            if new_owner.uuid == team.owner_uuid:
                raise ValueError("Пользователь уже является владельцем команды")

            if new_owner.team_uuid != team.uuid:
                raise ValueError("Новый владелец должен быть участником команды")

            if not new_owner.is_active:
                raise ValueError("Новый владелец должен быть активным пользователем")

            # 4. Передать владение
            team.owner_uuid = new_owner.uuid
            await self._team_repo.update_team(team)
            await self._db_session.commit()

            return True

        except Exception:
            await self._db_session.rollback()
            raise


class GenerateInviteCodeInteractor:
    """Интерактор для генерации кода приглашения в команду"""

    # Простое хранилище кодов в памяти (в реальном проекте - Redis/БД)
    _invite_codes: Dict[str, Dict] = {}

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        code_ttl_hours: int = 24,
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._code_ttl_hours = code_ttl_hours

    async def __call__(
        self,
        actor_uuid: UUID,
        team_uuid: UUID,
    ) -> str:
        """Сгенерировать код приглашения"""

        # 1. Найти участников
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        team = await self._team_repo.get_by_uuid(team_uuid)

        if not actor:
            raise ValueError("Пользователь не найден")
        if not team:
            raise ValueError("Команда не найдена")

        # 2. Проверить права доступа
        if self._permission_validator:
            if not await self._permission_validator.can_add_team_member(actor, team):
                raise PermissionError("Нет прав для создания приглашений")
        else:
            # Временная простая проверка
            is_owner = team.owner_uuid == actor.uuid
            is_admin = actor.role == RoleEnum.ADMIN
            is_manager_same_team = (
                actor.role == RoleEnum.MANAGER and actor.team_uuid == team.uuid
            )

            if not (is_owner or is_admin or is_manager_same_team):
                raise PermissionError(
                    "Только владелец команды, админ или менеджер команды может создавать приглашения"
                )

        # 3. Сгенерировать уникальный код
        invite_code = self._generate_unique_code()
        expires_at = datetime.now() + timedelta(hours=self._code_ttl_hours)

        # 4. Сохранить код
        self._invite_codes[invite_code] = {
            "team_uuid": str(team_uuid),
            "created_by": str(actor_uuid),
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "is_active": True,
        }

        return invite_code

    def _generate_unique_code(self) -> str:
        """Сгенерировать уникальный код приглашения"""
        while True:
            code = secrets.token_urlsafe(8)  # 8 символов
            if code not in self._invite_codes:
                return code

    @classmethod
    def get_team_by_invite_code(cls, invite_code: str) -> Optional[str]:
        """Получить UUID команды по коду приглашения"""
        if invite_code not in cls._invite_codes:
            return None

        invite_data = cls._invite_codes[invite_code]

        # Проверить активность и срок действия
        if not invite_data["is_active"]:
            return None

        if datetime.now() > invite_data["expires_at"]:
            # Деактивировать истекший код
            invite_data["is_active"] = False
            return None

        return invite_data["team_uuid"]

    @classmethod
    def invalidate_invite_code(cls, invite_code: str) -> bool:
        """Деактивировать код приглашения"""
        if invite_code in cls._invite_codes:
            cls._invite_codes[invite_code]["is_active"] = False
            return True
        return False


class JoinTeamByInviteCodeInteractor:
    """Интерактор для присоединения к команде по коду приглашения"""

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        db_session: DBSession,
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._db_session = db_session

    async def __call__(
        self,
        user_uuid: UUID,
        invite_code: str,
    ) -> bool:
        """Присоединиться к команде по коду приглашения"""

        try:
            # 1. Найти пользователя
            user = await self._user_repo.get_by_uuid(user_uuid)
            if not user:
                raise ValueError("Пользователь не найден")

            # 2. Проверить код приглашения
            team_uuid_str = GenerateInviteCodeInteractor.get_team_by_invite_code(
                invite_code
            )
            if not team_uuid_str:
                raise ValueError("Недействительный или истекший код приглашения")

            team_uuid = UUID(team_uuid_str)
            team = await self._team_repo.get_by_uuid(team_uuid)
            if not team:
                raise ValueError("Команда не найдена")

            # 3. Бизнес-валидация
            if user.team_uuid is not None:
                if user.team_uuid == team.uuid:
                    raise ValueError("Вы уже состоите в этой команде")
                else:
                    raise ValueError("Вы уже состоите в другой команде")

            if not user.is_active:
                raise ValueError(
                    "Неактивные пользователи не могут присоединяться к командам"
                )

            # 4. Присоединиться к команде
            user.team_uuid = team.uuid
            await self._user_repo.update_user(user)

            # 5. Деактивировать использованный код (опционально)
            # GenerateInviteCodeInteractor.invalidate_invite_code(invite_code)

            await self._db_session.commit()
            return True

        except Exception:
            await self._db_session.rollback()
            raise


class GetTeamMembersInteractor:
    """Интерактор для получения списка участников команды"""

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
        team_uuid: UUID,
    ) -> List[User]:
        """Получить список участников команды"""

        # 1. Найти актора и команду
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        team = await self._team_repo.get_by_uuid(team_uuid)

        if not actor:
            raise ValueError("Пользователь не найден")
        if not team:
            raise ValueError("Команда не найдена")

        # 2. Проверить права доступа
        if self._permission_validator:
            if not await self._permission_validator.can_view_team_members(actor, team):
                raise PermissionError("Нет прав для просмотра участников команды")
        else:
            # Временная простая проверка
            is_member = actor.team_uuid == team.uuid
            is_admin = actor.role == RoleEnum.ADMIN
            is_manager = actor.role == RoleEnum.MANAGER

            if not (is_member or is_admin or is_manager):
                raise PermissionError(
                    "Только участники команды, админы или менеджеры могут просматривать состав команды"
                )

        # 3. Получить участников
        members = await self._user_repo.get_team_members(team.uuid)
        return members
