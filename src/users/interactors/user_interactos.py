from datetime import date
from typing import (
    List,
    Optional,
)
from uuid import UUID

from core.interfaces import (
    DBSession,
    PermissionValidator,
    UUIDGenerator,
)
from teams.interfaces import TeamRepository
from teams.interfaces import (
    TeamMembershipManager,
)
from users.interfaces import (
    PasswordHasher,
    UserActivationManager,
    UserRepository,
    UserValidator,
)
from users.models import (
    GenderEnum,
    RoleEnum,
    User,
)
from users.schemas import (
    UserUpdate,
)


class CreateUserDTO:
    """DTO для создания пользователя (внутренний доменный объект)"""

    def __init__(
        self,
        email: str,
        name: str,
        surname: str,
        gender: GenderEnum,
        birth_date: date,
        password: str,
        role: Optional[RoleEnum] = None,
        team_uuid: Optional[UUID] = None,
    ) -> None:
        self.email = email
        self.name = name
        self.surname = surname
        self.gender = gender
        self.birth_date = birth_date
        self.password = password
        self.role = role or RoleEnum.EMPLOYEE
        self.team_uuid = team_uuid


class CreateUserInteractor:
    """Интерактор для создания нового пользователя"""

    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher,
        user_validator: UserValidator,
        permission_validator: PermissionValidator,
        uuid_generator: UUIDGenerator,
        db_session: DBSession,
        activate_manager: UserActivationManager,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._user_validator = user_validator
        self._permission_validator = permission_validator
        self._uuid_generator = uuid_generator
        self._db_session = db_session
        self._activate_manager = activate_manager

    async def __call__(
        self,
        actor_uuid: Optional[UUID],
        dto: CreateUserDTO,
    ) -> User:
        """
        Создание нового пользователя

        Args:
            actor_uuid: кто создает пользователя (None - для самостоятельной регистрации)
            dto: данные для создания пользователя
        """
        # 1. Самостоятельная регистрация

        try:
            if actor_uuid is None:
                if dto.role != RoleEnum.EMPLOYEE:
                    raise PermissionError(
                        "При самостоятельной регистрации доступная роль только EMPLOYEE"
                    )
                dto.role = RoleEnum.EMPLOYEE
                dto.team_uuid = None

            # Создание другим пользователем

            else:
                actor = await self._user_repo.get_by_uuid(actor_uuid)
                if not actor:
                    raise ValueError("Пользователь-создатель не найден")

                if not await self._permission_validator.is_system_admin(actor):
                    raise PermissionError("Нет прав для создания пользователей")

                # TODO: добавить проверку существования команды, когда создадим TeamRepository
                # Пока проверка идет по FK constraint

            # 2. Бизнес-валдиация

            if not self._user_validator.validate_age(dto.birth_date):
                raise ValueError("Пользователь должен быть старше 16 лет")

            if not self._user_validator.validate_password_strength(dto.password):
                raise ValueError("Пароль не соотвествует требованиям безопасности")

            if not await self._user_validator.validate_email_unique(dto.email):
                raise ValueError(f"Email: {dto.email} уже используется")

            # 3. Создание доменной сущности
            user_uuid = self._uuid_generator()
            hashed_passowrd = self._password_hasher.hash_password(dto.password)

            user = User(
                uuid=user_uuid,
                email=dto.email,
                password=hashed_passowrd,
                name=dto.name,
                surname=dto.surname,
                gender=dto.gender,
                birth_date=dto.birth_date,
                role=dto.role,
                team_uuid=dto.team_uuid,
                is_active=True,
                is_verified=False,
            )

            # 4. Сохранение
            created_user = await self._user_repo.create_user(user)
            await self._db_session.flush()

            # 5. Генерация токена верификации email
            verification_token = (
                await self._activate_manager.generate_verification_token(
                    created_user.uuid
                )
            )

            await self._db_session.commit()

            # TODO: Отправить email с токеном верификации
            return created_user

        except Exception:
            await self._db_session.rollback()
            raise


class GetUserInteractor:
    """Интерактор для получения пользователя"""

    def __init__(
        self,
        user_repo: UserRepository,
        permission_validator: PermissionValidator,
    ) -> None:
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def get_by_uuid(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
    ) -> Optional[User]:
        """Получить пользователя по UUID с проверкой прав"""

        # 1. Получить участников

        actor = await self._user_repo.get_by_uuid(actor_uuid)
        target = await self._user_repo.get_by_uuid(target_uuid)

        if not actor or not target:
            return None

        # 2. Проверить права доступа

        if not await self._permission_validator.can_view_user(
            actor,
            target,
        ):
            raise PermissionError("Нет прав для просмотра данных пользователя")

        return target

    async def get_by_email(
        self,
        actor_uuid: UUID,
        email: str,
    ) -> Optional[User]:
        """Получить пользователя по email с проверкой прав"""
        # 1. Получить пользователей

        actor = await self._user_repo.get_by_uuid(actor_uuid)
        target = await self._user_repo.get_by_email(email)

        if not actor or not target:
            return None

        # 2. Проверка прав просмотра

        if not await self._permission_validator.can_view_user(
            actor,
            target,
        ):
            raise PermissionError("Нет прав для просмотра данных пользователя")

        return target


class GetUsersWithoutTeamInteractor:
    """Интерактор для получения пользователей без команды"""

    def __init__(
        self,
        user_repo: UserRepository,
        permission_validator: PermissionValidator,
    ):
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[User]:
        """Получить пользоваетелей без команды с проверкой прав"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Проверить права
        if not await self._permission_validator.can_view_users_without_team(actor):
            raise PermissionError("нет прав для просмотра пользователей без команды")

        # 3. Получить данные
        return await self._user_repo.get_users_without_team(limit, offset)


class UpdateUserInteractor:
    """Интерактор для обновления пользователя"""

    def __init__(
        self,
        user_repo: UserRepository,
        user_validator: UserValidator,
        permission_validator: PermissionValidator,
        db_session: DBSession,
    ) -> None:
        self._user_repo = user_repo
        self._user_validator = user_validator
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
        update_data: UserUpdate,
    ) -> User:
        """Обновить данные пользователя"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            target = await self._user_repo.get_by_uuid(target_uuid)

            if not actor:
                raise ValueError("Пользователь actor не найден")
            if not target:
                raise ValueError("Обновляемый пользователь не найден")

            # 2. Проверить права доступа

            if not await self._permission_validator.can_update_user(
                actor,
                target,
            ):
                raise PermissionError("Нет прав для обновления пользователей")

            # 3. Валидация изменений

            if update_data.name is not None:
                target.name = update_data.name

            if update_data.surname is not None:
                target.surname = update_data.surname

            if update_data.gender is not None:
                target.gender = update_data.gender

            if update_data.birth_date is not None:
                # Проверяем возраст пользователя
                if not self._user_validator.validate_age(update_data.birth_date):
                    raise ValueError(
                        "Недопустимый возраст! (Должен быть старше 16 лет)"
                    )
                target.birth_date = update_data.birth_date

            if update_data.role is not None:
                # Проеряем права назначения роли
                if not await self._permission_validator.can_assign_role(
                    actor,
                    target,
                    update_data.role.value,
                ):
                    raise PermissionError("Нет прав для назначение этой роли")
                target.role = update_data.role

            # 4. Сохранение
            updated_user = await self._user_repo.update_user(target)
            await self._db_session.commit()
            return updated_user

        except Exception:
            await self._db_session.rollback()
            raise


class DeleteUserInteractor:
    """Интерактор для удаления пользователя"""

    def __init__(
        self,
        user_repo: UserRepository,
        permission_validator: PermissionValidator,
        db_session: DBSession,
    ) -> None:
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
    ) -> bool:
        """Удалить пользователя"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            target = await self._user_repo.get_by_uuid(target_uuid)

            if not actor:
                raise ValueError("Пользователь actor не найден")
            if not target:
                raise ValueError("Удаляемый пользователь не найден")

            # 2. Проверить права доступа

            if not await self._permission_validator.can_delete_user(
                actor,
                target,
            ):
                raise PermissionError("Нет прав для удаления пользователей")

            # 3. Удаление

            result = await self._user_repo.delete_user(target_uuid)
            if result:
                await self._db_session.commit()

            return result

        except Exception:
            await self._db_session.rollback()
            raise


class JoinTeamByCodeInteractor:
    """Интерактор для присоединения к команде по коду"""

    def __init__(
        self,
        user_repo: UserRepository,
        team_membership_manager: TeamMembershipManager,
        permission_validator: PermissionValidator,
        db_session: DBSession,
    ) -> None:
        self._user_repo = user_repo
        self._team_membership_manager = team_membership_manager
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
        invite_code: str,
    ) -> bool:
        """Присоединиться к команде по коду приглашения"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            target = await self._user_repo.get_by_uuid(target_uuid)

            if not actor:
                raise ValueError("Пользователь-инициатор не найден")
            if not target:
                raise ValueError("Пользователь не найден")

            # 2. Проверить права доступа
            is_self_action = target.uuid == actor.uuid
            is_admin = actor.role == RoleEnum.ADMIN

            if not is_self_action and not is_admin:
                raise PermissionError("Вы можете присоединить только себя к команде")

            # 3. Бизнес-правила
            if target.team_uuid:
                raise ValueError("Пользователь уже состоит в команде")

            # 4. Присоединиться к команде

            result = await self._team_membership_manager.join_team_by_code(
                target.uuid,
                invite_code,
            )
            if result:
                await self._db_session.commit()
            return result

        except Exception:
            await self._db_session.rollback()
            raise


class QueryUserInteractor:
    """Интерактор для получения списка пользователей с проверкой прав доступа"""

    def __init__(
        self,
        user_repo: UserRepository,
        team_repo: TeamRepository,
        permission_validator: PermissionValidator,
    ) -> None:
        self._user_repo = user_repo
        self._team_repo = team_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
        team_uuid: Optional[UUID] = None,
        search_query: Optional[str] = None,
        exclude_team: bool = False,
    ) -> List[User]:
        """
        Получить список пользователей с проверкой прав доступа

        Args:
            actor_uuid: UUID пользователя, запрашивающего список
            limit: Максимальное количество пользователей
            offset: Смещение для пагинации
            team_uuid: UUID команды для фильтрации (опционально)
            search_query: Поисковый запрос
            exclude_team: Исключить пользователей из указанной команды

        Returns:
            Список пользователей, доступных для просмотра
        """
        # 1. Найти пользователя, который запрашивает список
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить базовый фильтр на основе роли
        final_team_uuid = self._determine_team_filter(
            actor,
            team_uuid,
        )

        # 3. Если запрашивается конкретная команда - проверить права
        if team_uuid:
            await self._check_team_access_permission(
                actor,
                team_uuid,
            )

        # 4. Получить пользователей
        if search_query:
            users = await self._user_repo.search_users(
                query=search_query,
                team_uuid=final_team_uuid,
                exclude_team=exclude_team,
                limit=limit,
            )
        else:
            users = await self._user_repo.list_users(
                limit=limit,
                offset=offset,
                team_uuid=final_team_uuid,
            )

        return users

    def _determine_team_filter(
        self,
        actor: User,
        requested_team_uuid: Optional[UUID],
    ) -> Optional[UUID]:
        """
        Определить базовый фильтр команды на основе роли пользователя

        Args:
            actor: Пользователь, запрашивающий список
            requested_team_uuid: Запрошенная команда (может быть None)

        Returns:
            UUID команды для фильтрации или None
        """
        # Сотрудники видят только свою команду
        if actor.role == RoleEnum.EMPLOYEE:
            return actor.team_uuid

        # Админы и менеджеры могут указывать любую команду
        return requested_team_uuid

    async def _check_team_access_permission(
        self,
        actor: User,
        team_uuid: UUID,
    ) -> None:
        """
        Проверить права доступа к конкретной команде

        Args:
            actor: Пользователь, запрашивающий список
            team_uuid: UUID команды для проверки
        """
        # Найти команду
        team = await self._team_repo.get_by_uuid(team_uuid)
        if not team:
            raise ValueError("Команда не найдена")

        # Проверить права через PermissionValidator
        can_view = await self._permission_validator.can_view_team_members(
            actor,
            team,
        )
        if not can_view:
            raise PermissionError("Нет прав для просмотра участников этой команды")


class AssignRoleInteractor:
    """Интерактор для назначения роли пользователю"""

    def __init__(
        self,
        user_repo: UserRepository,
        permission_validator: PermissionValidator,
        db_session: DBSession,
    ) -> None:
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
        new_role: RoleEnum,
    ) -> bool:
        """Назначить роль пользователю"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            target = await self._user_repo.get_by_uuid(target_uuid)

            if not actor:
                raise ValueError("Пользователь-назначающий не найден")
            if not target:
                raise ValueError("Пользователь для назначения роли не найден")

            # 2. Проверить права доступа
            if not await self._permission_validator.can_assign_role(
                actor,
                target,
                new_role.value,
            ):
                raise PermissionError("Нет прав для назначения роли")

            # 3. Бизнес-правила
            if target.uuid == actor.uuid and new_role == RoleEnum.EMPLOYEE:
                raise ValueError("Администратор не может понизить себя до EMPLOYEE")

            # 4. Назначить роль
            target.role = new_role
            await self._user_repo.update_user(target)
            await self._db_session.commit()

            return True

        except Exception:
            await self._db_session.rollback()
            raise


class RemoveRoleInteractor:
    """Интерактор для убирания роли пользователя (делает EMPLOYEE)"""

    def __init__(
        self,
        user_repo: UserRepository,
        permission_validator: PermissionValidator,
        db_session: DBSession,
    ) -> None:
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
    ) -> bool:
        """Убрать роль пользователя (сделать EMPLOYEE)"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            target = await self._user_repo.get_by_uuid(target_uuid)

            if not actor:
                raise ValueError("Пользователь-назначающий не найден")
            if not target:
                raise ValueError("Пользователь не найден")

            # 2. Проверить права доступа
            if not await self._permission_validator.can_assign_role(
                actor,
                target,
                RoleEnum.EMPLOYEE.value,
            ):
                raise PermissionError("Нет прав для изменения роли")
            else:
                # Временная простая проверка
                if actor.role != RoleEnum.ADMIN:
                    raise PermissionError("Только администраторы могут убирать роли")

            # 3. Бизнес-правила
            if target.uuid == actor.uuid:
                raise ValueError("Нельзя убрать роль у самого себя")

            # 4. Убрать роль
            target.role = RoleEnum.EMPLOYEE
            await self._user_repo.update_user(target)
            await self._db_session.commit()

            return True

        except Exception:
            await self._db_session.rollback()
            raise


class LeaveTeamInteractor:
    """Интерактор для выхода из команды"""

    def __init__(
        self,
        user_repo: UserRepository,
        permission_validator: PermissionValidator,
        db_session: DBSession,
    ) -> None:
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
    ) -> bool:
        """Покинуть команду"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            target = await self._user_repo.get_by_uuid(target_uuid)

            if not actor:
                raise ValueError("Пользователь-инициатор не найден")
            if not target:
                raise ValueError("Пользователь не найден")

            # 2. Проверить права доступа
            is_self_action = target.uuid == actor.uuid
            is_admin = actor.role == RoleEnum.ADMIN

            if not is_self_action and not is_admin:
                # TODO: Добавить проверку через PermissionValidator
                pass
                raise PermissionError("Вы можете удалить из команды только себя")

            # 3. Бизнес-правила
            if not target.team_uuid:
                raise ValueError("Пользователь не состоит в команде")

            # TODO: Проверить, не является ли пользователь владельцем команды
            # (эта проверка будет добавлена когда реализуем Teams)

            # 4. Покинуть команду
            target.team_uuid = None
            await self._user_repo.update_user(target)
            await self._db_session.commit()

            return True

        except Exception:
            await self._db_session.rollback()
            raise


class GetUserStatsInteractor:
    """Интерактор для получения статистики пользователя"""

    def __init__(
        self,
        user_repo: UserRepository,
        permission_validator: PermissionValidator,
    ) -> None:
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
    ) -> dict:
        """Получить статистику пользователя"""

        # 1. Найти участников
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        target = await self._user_repo.get_by_uuid(target_uuid)

        if not actor:
            raise ValueError("Пользователь-запрашивающий не найден")
        if not target:
            raise ValueError("Пользователь не найден")

        # 2. Проверить права доступа
        if not await self._permission_validator.can_view_user(
            actor,
            target,
        ):
            raise PermissionError("Нет прав для просмотра статистики")
        else:
            # Временная простая проверка
            is_self = target.uuid == actor.uuid
            is_manager_or_admin = actor.role in [RoleEnum.ADMIN, RoleEnum.MANAGER]

            if not is_self and not is_manager_or_admin:
                raise PermissionError("Нет прав для просмотра статистики")

        # 3. Собрать статистику
        return {
            "user_uuid": str(target.uuid),
            "email": target.email,
            "name": f"{target.name} {target.surname}",
            "role": target.role.value if target.role else "EMPLOYEE",
            "is_active": target.is_active,
            "is_verified": target.is_verified,
            "team_uuid": str(target.team_uuid) if target.team_uuid else None,
            "created_at": target.created_at.isoformat(),
            # Заглушки для статистики
            
            #TODO добавить после реализации Task и Evaluation
            "tasks_stats": {
                "total_assigned": 0,
                "completed": 0,
                "in_progress": 0,
                "overdue": 0,
            },
            "evaluation_stats": {
                "average_score": 0.0,
                "total_evaluations": 0,
                "last_evaluation": None,
            },
            "meetings_stats": {"upcoming": 0, "total_participated": 0},
        }
