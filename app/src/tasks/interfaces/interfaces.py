from typing import (
    List,
    Optional,
    Protocol,
)
from uuid import UUID

from tasks.models import (
    StatusEnum,
    Task,
)


class TaskRepository(Protocol):
    """Интерфейс для работы с задачами в хранилище данных"""

    async def create_task(self, task: Task) -> Task:
        """Создать новую задачу"""
        ...

    async def get_by_uuid(self, task_uuid: UUID) -> Optional[Task]:
        """Получить задачу по UUID"""
        ...

    async def update_task(self, task: Task) -> Task:
        """Обновить задачу"""
        ...

    async def delete_task(self, task_uuid: UUID) -> bool:
        """Удалить задачу"""
        ...

    async def list_tasks(
        self,
        limit: int = 50,
        offset: int = 0,
        team_uuid: Optional[UUID] = None,
        assignee_uuid: Optional[UUID] = None,
        creator_uuid: Optional[UUID] = None,
        status: Optional[StatusEnum] = None,
    ) -> List[Task]:
        """Получить список задач с фильтрацией"""
        ...

    async def get_user_tasks(
        self,
        user_uuid: UUID,
        status: Optional[StatusEnum] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Task]:
        """Получить задачи пользователя (созданные или назначенные)"""
        ...

    async def get_team_tasks(
        self,
        team_uuid: UUID,
        status: Optional[StatusEnum] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Task]:
        """Получить задачи команды"""
        ...

    async def get_overdue_tasks(
        self,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Task]:
        """Получить просроченные задачи"""
        ...

    async def search_tasks(
        self,
        query: str,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Task]:
        """Поиск задач по названию или описанию"""
        ...

    async def get_task_with_relations(self, task_uuid: UUID) -> Optional[Task]:
        """Получить задачу с загруженными связями (assignee, creator, team)"""
        ...

    async def count_tasks_by_status(
        self,
        team_uuid: Optional[UUID] = None,
        assignee_uuid: Optional[UUID] = None,
    ) -> dict[StatusEnum, int]:
        """Получить количество задач по статусам"""
        ...
