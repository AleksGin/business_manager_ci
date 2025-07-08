from typing import (
    List,
    Optional,
    Protocol,
)
from uuid import UUID

from teams.models import Team


class TeamRepository(Protocol):
    """Интерфейс для работы с командами в хранилище данных"""

    async def create_team(self, team: Team) -> Team:
        """Создать новую команду"""
        ...

    async def get_by_uuid(self, team_uuid: UUID) -> Optional[Team]:
        """Получить команду по UUID"""
        ...

    async def get_by_name(self, name: str) -> Optional[Team]:
        """Получить команду по названию"""
        ...

    async def update_team(self, team: Team) -> Team:
        """Обновить команду"""
        ...

    async def delete_team(self, team_uuid: UUID) -> bool:
        """Удалить команду"""
        ...

    async def get_user_teams(self, user_uuid: UUID) -> List[Team]:
        """Получить команды, где пользователь является владельцем"""
        ...

    async def list_teams(
        self,
        limit: int = 50,
        offset: int = 0,
        owner_uuid: Optional[UUID] = None,
    ) -> List[Team]:
        """Получить список команд с пагинацией и фильтрацией"""
        ...

    async def exists_by_name(self, name: str) -> bool:
        """Проверить существование команды по названию"""
        ...

    async def get_team_with_members(self, team_uuid: UUID) -> Optional[Team]:
        """Получить команду с загруженными участниками"""
        ...

    async def search_teams(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Team]:
        """Поиск команд по названию или описанию"""
        ...


class TeamMembershipManager(Protocol):
    """Интерфейс для управления членством пользователей в командах"""

    async def add_user_to_team(
        self,
        user_uuid: UUID,
        team_uuid: UUID,
        added_by: UUID,
    ) -> bool:
        """
        Добавить пользователя в команду.

        Args:
            user_uuid: кого добавляем
            team_uuid: в какую команду
            added_by: кто добавляет
        """
        ...

    async def remove_user_from_team(
        self,
        user_uuid: UUID,
        team_uuid: UUID,
        removed_by: UUID,
    ) -> bool:
        """
        Удалить пользователя из команды.

        Args:
            user_uuid: кого удаляем
            team_uuid: из какой команды
            removed_by: кто удаляет
        """
        ...

    async def transfer_team_ownership(
        self,
        team_uuid: UUID,
        new_owner_uuid: UUID,
        current_owner_uuid: UUID,
    ) -> bool:
        """
        Передать владение командой другому пользователю.

        Args:
            team_uuid: команда для передачи
            new_owner_uuid: новый владелец
            current_owner_uuid: текущий владелец (для проверки прав)
        """
        ...

    async def generate_team_invite_code(
        self,
        team_uuid: UUID,
        created_by: UUID,
    ) -> str:
        """
        Создать код приглашения в команду.

        Returns:
            строка-код для присоединения к команде
        """
        ...

    async def join_team_by_code(
        self,
        user_uuid: UUID,
        invite_code: str,
    ) -> bool:
        """
        Присоединиться к команде используя код приглашения.

        Args:
            user_uuid: кто присоединяется
            invite_code: код приглашения
        """
        ...
