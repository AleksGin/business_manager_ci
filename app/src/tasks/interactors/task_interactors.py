from datetime import datetime
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
from tasks.interfaces import TaskRepository
from tasks.models import Task, StatusEnum
from tasks.schemas.task import TaskUpdate
from teams.interfaces import TeamRepository
from users.interfaces import UserRepository
from users.models import RoleEnum


class CreateTaskDTO:
    """DTO для создания задачи"""

    def __init__(
        self,
        title: str,
        description: Optional[str],
        deadline: datetime,
        team_uuid: UUID,
        creator_uuid: UUID,
        assignee_uuid: Optional[UUID] = None,
    ) -> None:
        self.title = title
        self.description = description
        self.deadline = deadline
        self.team_uuid = team_uuid
        self.creator_uuid = creator_uuid
        self.assignee_uuid = assignee_uuid


class CreateTaskInteractor:
    """Интерактор для создания задачи"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        team_repo: TeamRepository,
        permission_validator: Optional[PermissionValidator],
        uuid_generator: UUIDGenerator,
        db_session: DBSession,
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._team_repo = team_repo
        self._permission_validator = permission_validator
        self._uuid_generator = uuid_generator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        dto: CreateTaskDTO,
    ) -> Task:
        """Создать новую задачу"""

        try:
            # 1. Найти актора
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            if not actor:
                raise ValueError("Пользователь не найден")

            # 2. Проверить команду
            team = await self._team_repo.get_by_uuid(dto.team_uuid)
            if not team:
                raise ValueError("Команда не найдена")

            # 3. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_create_task(actor, team):
                    raise PermissionError("Нет прав для создания задач в этой команде")
            else:
                # Временная простая проверка
                is_team_member = actor.team_uuid == team.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_team_member or is_admin):
                    raise PermissionError(
                        "Только участники команды могут создавать задачи"
                    )

            # 4. Проверить исполнителя (если указан)
            assignee = None
            if dto.assignee_uuid:
                assignee = await self._user_repo.get_by_uuid(dto.assignee_uuid)
                if not assignee:
                    raise ValueError("Назначаемый исполнитель не найден")

                # Исполнитель должен быть участником команды
                if assignee.team_uuid != team.uuid:
                    raise ValueError("Исполнитель должен быть участником команды")

            # 5. Бизнес-валидация
            if dto.deadline <= datetime.now():
                raise ValueError("Дедлайн должен быть в будущем")

            # 6. Создать задачу
            task_uuid = self._uuid_generator()

            task = Task(
                uuid=task_uuid,
                title=dto.title,
                description=dto.description,
                deadline=dto.deadline,
                status=StatusEnum.OPENED,
                assignee_uuid=dto.assignee_uuid,
                team_uuid=dto.team_uuid,
                creator_uuid=dto.creator_uuid,
            )

            # 7. Сохранить
            created_task = await self._task_repo.create_task(task)
            await self._db_session.commit()
            return created_task

        except Exception:
            await self._db_session.rollback()
            raise


class GetTaskInteractor:
    """Интерактор для получения задачи"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def get_by_uuid(
        self,
        actor_uuid: UUID,
        task_uuid: UUID,
        with_relations: bool = False,
    ) -> Optional[Task]:
        """Получить задачу по UUID"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Получить задачу
        if with_relations:
            task = await self._task_repo.get_task_with_relations(task_uuid)
        else:
            task = await self._task_repo.get_by_uuid(task_uuid)

        if not task:
            return None

        # 3. Проверить права доступа
        if self._permission_validator:
            if not await self._permission_validator.can_view_task(actor, task):
                raise PermissionError("Нет прав для просмотра задачи")
        else:
            # Временная простая проверка
            is_team_member = actor.team_uuid == task.team_uuid
            is_assignee = task.assignee_uuid == actor.uuid
            is_creator = task.creator_uuid == actor.uuid
            is_admin = actor.role == RoleEnum.ADMIN

            if not (is_team_member or is_assignee or is_creator or is_admin):
                raise PermissionError("Нет прав для просмотра задачи")

        return task


class UpdateTaskInteractor:
    """Интерактор для обновления задачи"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        task_uuid: UUID,
        update_data: TaskUpdate,
    ) -> Task:
        """Обновить задачу"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            task = await self._task_repo.get_by_uuid(task_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not task:
                raise ValueError("Задача не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_update_task(actor, task):
                    raise PermissionError("Нет прав для обновления задачи")
            else:
                # Временная простая проверка
                is_creator = task.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN
                is_manager_same_team = (
                    actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid
                )

                if not (is_creator or is_admin or is_manager_same_team):
                    raise PermissionError(
                        "Только создатель, админ или менеджер команды может обновлять задачу"
                    )

            # 3. Валидация изменений
            if update_data.title is not None:
                task.title = update_data.title

            if update_data.description is not None:
                task.description = update_data.description

            if update_data.deadline is not None:
                if update_data.deadline <= datetime.now():
                    raise ValueError("Дедлайн должен быть в будущем")
                task.deadline = update_data.deadline

            if update_data.status is not None:
                task.status = update_data.status

            # Обновление исполнителя и команды - отдельные операции
            if update_data.assignee_uuid is not None:
                assignee = await self._user_repo.get_by_uuid(update_data.assignee_uuid)
                if not assignee:
                    raise ValueError("Назначаемый исполнитель не найден")
                if assignee.team_uuid != task.team_uuid:
                    raise ValueError("Исполнитель должен быть участником команды")
                task.assignee_uuid = update_data.assignee_uuid

            if update_data.team_uuid is not None:
                # Можно перенести задачу в другую команду (если есть права)
                task.team_uuid = update_data.team_uuid

            # 4. Сохранить
            updated_task = await self._task_repo.update_task(task)
            await self._db_session.commit()
            return updated_task

        except Exception:
            await self._db_session.rollback()
            raise


class DeleteTaskInteractor:
    """Интерактор для удаления задачи"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        task_uuid: UUID,
    ) -> bool:
        """Удалить задачу"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            task = await self._task_repo.get_by_uuid(task_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not task:
                raise ValueError("Задача не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_delete_task(actor, task):
                    raise PermissionError("Нет прав для удаления задачи")
            else:
                # Временная простая проверка
                is_creator = task.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_creator or is_admin):
                    raise PermissionError(
                        "Только создатель или админ может удалять задачу"
                    )

            # 3. Удалить задачу
            result = await self._task_repo.delete_task(task_uuid)
            if result:
                await self._db_session.commit()
            return result

        except Exception:
            await self._db_session.rollback()
            raise


class AssignTaskInteractor:
    """Интерактор для назначения исполнителя задачи"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        task_uuid: UUID,
        assignee_uuid: Optional[UUID],
    ) -> Task:
        """Назначить исполнителя задачи"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            task = await self._task_repo.get_by_uuid(task_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not task:
                raise ValueError("Задача не найдена")

            # 2. Проверить нового исполнителя
            assignee = None
            if assignee_uuid:
                assignee = await self._user_repo.get_by_uuid(assignee_uuid)
                if not assignee:
                    raise ValueError("Назначаемый исполнитель не найден")

                if assignee.team_uuid != task.team_uuid:
                    raise ValueError("Исполнитель должен быть участником команды")

            # 3. Проверить права доступа
            if self._permission_validator:
                if assignee:
                    if not await self._permission_validator.can_assign_task(
                        actor,
                        task,
                        assignee,
                    ):
                        raise PermissionError("Нет прав для назначения исполнителя")
            else:
                # Временная простая проверка
                is_creator = task.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN
                is_manager_same_team = (
                    actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid
                )

                if not (is_creator or is_admin or is_manager_same_team):
                    raise PermissionError(
                        "Только создатель, админ или менеджер команды может назначать исполнителя"
                    )

            # 4. Назначить исполнителя
            task.assignee_uuid = assignee_uuid
            updated_task = await self._task_repo.update_task(task)
            await self._db_session.commit()
            return updated_task

        except Exception:
            await self._db_session.rollback()
            raise


class ChangeTaskStatusInteractor:
    """Интерактор для смены статуса задачи"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        task_uuid: UUID,
        new_status: StatusEnum,
    ) -> Task:
        """Изменить статус задачи"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            task = await self._task_repo.get_by_uuid(task_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not task:
                raise ValueError("Задача не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_change_task_status(
                    actor, task
                ):
                    raise PermissionError("Нет прав для изменения статуса задачи")
            else:
                # Временная простая проверка
                is_assignee = task.assignee_uuid == actor.uuid
                is_creator = task.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN
                is_manager_same_team = (
                    actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid
                )

                if not (is_assignee or is_creator or is_admin or is_manager_same_team):
                    raise PermissionError(
                        "Только исполнитель, создатель, админ или менеджер команды может изменять статус"
                    )

            # 3. Бизнес-валидация переходов статусов
            if not self._is_valid_status_transition(task.status, new_status):
                raise ValueError(
                    f"Недопустимый переход статуса: {task.status.value} -> {new_status.value}"
                )

            # 4. Изменить статус
            task.status = new_status
            updated_task = await self._task_repo.update_task(task)
            await self._db_session.commit()
            return updated_task

        except Exception:
            await self._db_session.rollback()
            raise

    def _is_valid_status_transition(self, current: StatusEnum, new: StatusEnum) -> bool:
        """Проверить допустимость перехода статуса"""
        # Допустимые переходы
        valid_transitions = {
            StatusEnum.OPENED: [StatusEnum.IN_PROGRESS, StatusEnum.DONE],
            StatusEnum.IN_PROGRESS: [StatusEnum.OPENED, StatusEnum.DONE],
            StatusEnum.DONE: [
                StatusEnum.OPENED,
                StatusEnum.IN_PROGRESS,
            ],  # Можно "переоткрыть"
        }

        return new in valid_transitions.get(current, [])


class QueryTasksInteractor:
    """Интерактор для получения списка задач"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
        team_uuid: Optional[UUID] = None,
        assignee_uuid: Optional[UUID] = None,
        creator_uuid: Optional[UUID] = None,
        status: Optional[StatusEnum] = None,
        search_query: Optional[str] = None,
        show_overdue: bool = False,
    ) -> List[Task]:
        """Получить список задач с фильтрацией"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить доступные задачи на основе роли
        if actor.role == RoleEnum.EMPLOYEE:
            # Сотрудники видят только задачи своей команды
            final_team_uuid = actor.team_uuid
            if team_uuid and team_uuid != actor.team_uuid:
                raise PermissionError("Нет прав для просмотра задач другой команды")
        else:
            # Админы и менеджеры могут указывать команду
            final_team_uuid = team_uuid

        # 3. Получить задачи
        if show_overdue:
            tasks = await self._task_repo.get_overdue_tasks(
                team_uuid=final_team_uuid,
                limit=limit,
            )
        elif search_query:
            tasks = await self._task_repo.search_tasks(
                query=search_query,
                team_uuid=final_team_uuid,
                limit=limit,
            )
        else:
            tasks = await self._task_repo.list_tasks(
                limit=limit,
                offset=offset,
                team_uuid=final_team_uuid,
                assignee_uuid=assignee_uuid,
                creator_uuid=creator_uuid,
                status=status,
            )

        return tasks


class GetTaskStatsInteractor:
    """Интерактор для получения статистики задач"""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        team_uuid: Optional[UUID] = None,
        assignee_uuid: Optional[UUID] = None,
    ) -> dict:
        """Получить статистику задач"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Проверить права доступа
        if actor.role == RoleEnum.EMPLOYEE:
            # Сотрудники видят только статистику своей команды
            final_team_uuid = actor.team_uuid
            final_assignee_uuid = assignee_uuid

            if team_uuid and team_uuid != actor.team_uuid:
                raise PermissionError(
                    "Нет прав для просмотра статистики другой команды"
                )
        else:
            # Админы и менеджеры могут указывать параметры
            final_team_uuid = team_uuid
            final_assignee_uuid = assignee_uuid

        # 3. Получить статистику
        status_counts = await self._task_repo.count_tasks_by_status(
            team_uuid=final_team_uuid,
            assignee_uuid=final_assignee_uuid,
        )

        overdue_tasks = await self._task_repo.get_overdue_tasks(
            team_uuid=final_team_uuid,
            limit=100,  # Большой лимит для подсчета
        )

        return {
            "status_counts": {
                status.value: count for status, count in status_counts.items()
            },
            "total_tasks": sum(status_counts.values()),
            "overdue_count": len(overdue_tasks),
            "completion_rate": (
                status_counts[StatusEnum.DONE] / sum(status_counts.values()) * 100
                if sum(status_counts.values()) > 0
                else 0
            ),
        }
