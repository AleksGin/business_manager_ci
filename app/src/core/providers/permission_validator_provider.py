from typing import TYPE_CHECKING

from core.interfaces.permissions import PermissionValidator
from users.models import RoleEnum

if TYPE_CHECKING:
    from meetings.models import Meeting
    from tasks.models import Task
    from teams.models import Team
    from users.models import User


class PermissionValidatorProvider(PermissionValidator):
    """Централизованная система проверки прав доступа"""

    # ========== USER PERMISSIONS ==========

    async def can_view_user(
        self,
        actor: "User",
        target_user: "User",
    ) -> bool:
        """Проверка прав на просмотр пользователя"""
        # Админы видят всех
        if actor.role == RoleEnum.ADMIN:
            return True

        # Пользователь может видеть себя
        if actor.uuid == target_user.uuid:
            return True

        # Менеджеры видят участников своей команды и пользователей без команды
        if actor.role == RoleEnum.MANAGER:
            # Участники той же команды (оба должны быть в команде)
            if actor.team_uuid is not None and actor.team_uuid == target_user.team_uuid:
                return True
            # Пользователи без команды (для приглашения)
            if target_user.team_uuid is None:
                return True

        # Сотрудники видят только участников своей команды
        if actor.role == RoleEnum.EMPLOYEE:
            return (
                actor.team_uuid is not None and actor.team_uuid == target_user.team_uuid
            )

        return False

    async def can_assign_role(
        self,
        actor: "User",
        target_user: "User",
        new_role: str,
    ) -> bool:
        """Проверка прав на назначение роли"""
        # Только админы могут назначать роли
        if actor.role != RoleEnum.ADMIN:
            return False

        # Нельзя изменить роль самому себе на EMPLOYEE
        if actor.uuid == target_user.uuid and new_role == RoleEnum.EMPLOYEE.value:
            return False

        return True

    async def can_delete_user(
        self,
        actor: "User",
        target_user: "User",
    ) -> bool:
        """Проверка прав на удаление пользователя"""
        # Только админы могут удалять пользователей
        if actor.role != RoleEnum.ADMIN:
            return False

        # Нельзя удалить самого себя
        if actor.uuid == target_user.uuid:
            return False

        return True

    async def can_update_user(
        self,
        actor: "User",
        target_user: "User",
    ) -> bool:
        """Проверка прав на обновление пользователя"""
        # Админы могут обновлять всех
        if actor.role == RoleEnum.ADMIN:
            return True

        # Пользователь может обновлять себя (кроме роли и команды)
        if actor.uuid == target_user.uuid:
            return True

        return False

    async def can_view_users_without_team(self, actor: "User") -> bool:
        """Проверка прав на просмотр пользователей без команды"""
        # Админы и менеджеры могут видеть пользователей без команды
        return actor.role in [RoleEnum.ADMIN, RoleEnum.MANAGER]

    # ========== TEAM PERMISSIONS ==========

    async def can_create_team(self, actor: "User") -> bool:
        """Проверка прав на создание команды"""
        # Сотрудники не могут создавать команды
        return actor.role in [RoleEnum.ADMIN, RoleEnum.MANAGER]

    async def can_view_team(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на просмотр команды"""
        # Админы видят все команды
        if actor.role == RoleEnum.ADMIN:
            return True

        # Владелец команды
        if team.owner_uuid == actor.uuid:
            return True

        # Участник команды
        if actor.team_uuid == team.uuid:
            return True

        # Менеджеры могут видеть все команды
        if actor.role == RoleEnum.MANAGER:
            return True

        return False

    async def can_update_team(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на обновление команды"""
        # Админы могут обновлять все команды
        if actor.role == RoleEnum.ADMIN:
            return True

        # Владелец команды
        if team.owner_uuid == actor.uuid:
            return True

        return False

    async def can_delete_team(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на удаление команды"""
        # Админы могут удалять все команды
        if actor.role == RoleEnum.ADMIN:
            return True

        # Владелец команды
        if team.owner_uuid == actor.uuid:
            return True

        return False

    async def can_add_team_member(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на добавление участников в команду"""
        # Админы могут добавлять участников в любую команду
        if actor.role == RoleEnum.ADMIN:
            return True

        # Владелец команды
        if team.owner_uuid == actor.uuid:
            return True

        # Менеджеры могут добавлять участников в свою команду
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == team.uuid:
            return True

        return False

    async def can_remove_team_member(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на удаление участников из команды"""
        # Админы могут удалять участников из любой команды
        if actor.role == RoleEnum.ADMIN:
            return True

        # Владелец команды
        if team.owner_uuid == actor.uuid:
            return True

        # Менеджеры могут удалять участников из своей команды
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == team.uuid:
            return True

        return False

    async def can_view_team_members(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на просмотр участников команды"""
        # Админы видят участников всех команд
        if actor.role == RoleEnum.ADMIN:
            return True

        # Участники команды видят друг друга
        if actor.team_uuid == team.uuid:
            return True

        # Менеджеры видят участников всех команд
        if actor.role == RoleEnum.MANAGER:
            return True

        return False

    # ========== TASK PERMISSIONS ==========

    async def can_create_task(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на создание задач в команде"""
        # Админы могут создавать задачи в любой команде
        if actor.role == RoleEnum.ADMIN:
            return True

        # Участники команды могут создавать задачи
        if actor.team_uuid == team.uuid:
            return True

        return False

    async def can_view_task(
        self,
        actor: "User",
        task: "Task",
    ) -> bool:
        """Проверка прав на просмотр задачи"""
        # Админы видят все задачи
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель задачи
        if task.creator_uuid == actor.uuid:
            return True

        # Исполнитель задачи
        if task.assignee_uuid == actor.uuid:
            return True

        # Участники команды видят задачи команды
        if actor.team_uuid == task.team_uuid:
            return True

        return False

    async def can_delete_task(
        self,
        actor: "User",
        task: "Task",
    ) -> bool:
        """Проверка прав на удаление задачи"""
        # Админы могут удалять все задачи
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель задачи
        if task.creator_uuid == actor.uuid:
            return True

        return False

    async def can_assign_task(
        self,
        actor: "User",
        task: "Task",
        assignee: "User",
    ) -> bool:
        """Проверка прав на назначение исполнителя задачи"""
        # Админы могут назначать исполнителей
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель задачи
        if task.creator_uuid == actor.uuid:
            return True

        # Менеджеры могут назначать исполнителей в своей команде
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid:
            return True

        return False

    async def can_update_task(
        self,
        actor: "User",
        task: "Task",
    ) -> bool:
        """Проверка прав на обновление задачи"""
        # Админы могут обновлять все задачи
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель задачи
        if task.creator_uuid == actor.uuid:
            return True

        # Менеджеры могут обновлять задачи в своей команде
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid:
            return True

        return False

    async def can_change_task_status(
        self,
        actor: "User",
        task: "Task",
    ) -> bool:
        """Проверка прав на изменение статуса задачи"""
        # Админы могут изменять статус всех задач
        if actor.role == RoleEnum.ADMIN:
            return True

        # Исполнитель может изменять статус своих задач
        if task.assignee_uuid == actor.uuid:
            return True

        # Создатель задачи
        if task.creator_uuid == actor.uuid:
            return True

        # Менеджеры могут изменять статус задач в своей команде
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid:
            return True

        return False

    # ========== MEETING PERMISSIONS ==========

    async def can_create_meetings(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка прав на создание встреч в команде"""
        # Админы могут создавать встречи в любой команде
        if actor.role == RoleEnum.ADMIN:
            return True

        # Участники команды могут создавать встречи
        if actor.team_uuid == team.uuid:
            return True

        # Менеджеры могут создавать встречи в любой команде
        if actor.role == RoleEnum.MANAGER:
            return True

        return False

    async def can_update_meeting(
        self,
        actor: "User",
        meeting: "Meeting",
    ) -> bool:
        """Проверка прав на обновление встречи"""
        # Админы могут обновлять все встречи
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель встречи
        if meeting.creator_uuid == actor.uuid:
            return True

        return False

    async def can_delete_meeting(
        self,
        actor: "User",
        meeting: "Meeting",
    ) -> bool:
        """Проверка прав на удаление встречи"""
        # Админы могут удалять все встречи
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель встречи
        if meeting.creator_uuid == actor.uuid:
            return True

        return False

    async def can_add_meeting_participant(
        self,
        actor: "User",
        meeting: "Meeting",
    ) -> bool:
        """Проверка прав на добавление участников во встречу"""
        # Админы могут добавлять участников в любую встречу
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель встречи
        if meeting.creator_uuid == actor.uuid:
            return True

        # Менеджеры могут добавлять участников в встречи своей команды
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == meeting.team_uuid:
            return True

        return False

    # ========== EVALUATION PERMISSIONS ==========

    async def can_create_evaluation(
        self,
        actor: "User",
        task: "Task",
    ) -> bool:
        """Проверка прав на создание оценки для задачи"""
        # Админы могут создавать оценки для всех задач
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель задачи может оценить выполнение
        if task.creator_uuid == actor.uuid:
            return True

        # Менеджеры могут оценивать задачи в своей команде
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid:
            return True

        return False

    async def can_view_evaluation(
        self,
        actor: "User",
        task: "Task",
    ) -> bool:
        """Проверка прав на просмотр оценки задачи"""
        # Админы видят все оценки
        if actor.role == RoleEnum.ADMIN:
            return True

        # Участники команды видят оценки задач команды
        if actor.team_uuid == task.team_uuid:
            return True

        return False

    async def can_update_evaluation(
        self,
        actor: "User",
        task: "Task",
    ) -> bool:
        """Проверка прав на обновление оценки"""
        # Админы могут обновлять все оценки
        if actor.role == RoleEnum.ADMIN:
            return True

        # Создатель задачи может обновить оценку
        if task.creator_uuid == actor.uuid:
            return True

        # Менеджеры могут обновлять оценки в своей команде
        if actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid:
            return True

        return False

    # ========== SYSTEM PERMISSIONS ==========

    async def is_system_admin(self, actor: "User") -> bool:
        """Проверка, является ли пользователь системным администратором"""
        return actor.role == RoleEnum.ADMIN

    async def is_team_admin(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка, является ли пользователь администратором команды"""
        return team.owner_uuid == actor.uuid

    async def is_team_manager(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка, является ли пользователь менеджером команды"""
        return actor.role == RoleEnum.MANAGER and actor.team_uuid == team.uuid

    async def is_team_member(
        self,
        actor: "User",
        team: "Team",
    ) -> bool:
        """Проверка, является ли пользователь участником команды"""
        return actor.team_uuid == team.uuid
