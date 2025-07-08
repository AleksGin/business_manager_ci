from datetime import datetime
from typing import (
    List,
    Optional,
)
from uuid import UUID

from sqlalchemy import (
    and_,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tasks.interfaces import TaskRepository
from tasks.models import (
    StatusEnum,
    Task,
)


class TaskCRUD(TaskRepository):
    """Имплементация TaskRepository"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_task(self, task: Task) -> Task:
        """Создать новую задачу"""
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def get_by_uuid(self, task_uuid: UUID) -> Optional[Task]:
        """Получить задачу по UUID"""
        stmt = select(Task).where(Task.uuid == task_uuid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_task(self, task: Task) -> Task:
        """Обновить задачу"""
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def delete_task(self, task_uuid: UUID) -> bool:
        """Удалить задачу"""
        task = await self.get_by_uuid(task_uuid)

        if not task:
            return False

        await self._session.delete(task)
        await self._session.flush()
        return True

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
        stmt = select(Task)

        # Применяем фильтры
        conditions = []

        if team_uuid is not None:
            conditions.append(Task.team_uuid == team_uuid)

        if assignee_uuid is not None:
            conditions.append(Task.assignee_uuid == assignee_uuid)

        if creator_uuid is not None:
            conditions.append(Task.creator_uuid == creator_uuid)

        if status is not None:
            conditions.append(Task.status == status)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Пагинация и сортировка
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(Task.deadline.asc(), Task.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_tasks(
        self,
        user_uuid: UUID,
        status: Optional[StatusEnum] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Task]:
        """Получить задачи пользователя (созданные или назначенные)"""
        conditions = [
            or_(
                Task.assignee_uuid == user_uuid,
                Task.creator_uuid == user_uuid,
            )
        ]

        if status is not None:
            conditions.append(Task.status == status)

        stmt = select(Task).where(and_(*conditions))
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(Task.deadline.asc(), Task.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_tasks(
        self,
        team_uuid: UUID,
        status: Optional[StatusEnum] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Task]:
        """Получить задачи команды"""
        conditions = [Task.team_uuid == team_uuid]

        if status is not None:
            conditions.append(Task.status == status)

        stmt = select(Task).where(and_(*conditions))
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(Task.deadline.asc(), Task.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_overdue_tasks(
        self,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Task]:
        """Получить просроченные задачи"""
        now = datetime.now()

        conditions = [
            Task.deadline < now,
            Task.status != StatusEnum.DONE,  # Завершенные задачи не просрочены
        ]

        if team_uuid is not None:
            conditions.append(Task.team_uuid == team_uuid)

        stmt = select(Task).where(and_(*conditions))
        stmt = stmt.limit(limit)
        stmt = stmt.order_by(Task.deadline.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search_tasks(
        self,
        query: str,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Task]:
        """Поиск задач по названию или описанию"""
        search_pattern = f"%{query.lower()}%"

        conditions = [
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern),
            )
        ]

        if team_uuid is not None:
            conditions.append(Task.team_uuid == team_uuid)

        stmt = select(Task).where(and_(*conditions))
        stmt = stmt.limit(limit)
        stmt = stmt.order_by(Task.deadline.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_task_with_relations(self, task_uuid: UUID) -> Optional[Task]:
        """Получить задачу с загруженными связями"""
        stmt = select(Task).where(Task.uuid == task_uuid)
        stmt = stmt.options(
            selectinload(Task.assignee),  # Загружаем исполнителя
            selectinload(Task.creator),  # Загружаем создателя
            selectinload(Task.team),  # Загружаем команду
            selectinload(Task.evaluation),  # Загружаем оценку
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_tasks_by_status(
        self,
        team_uuid: Optional[UUID] = None,
        assignee_uuid: Optional[UUID] = None,
    ) -> dict[StatusEnum, int]:
        """Получить количество задач по статусам"""
        conditions = []

        if team_uuid is not None:
            conditions.append(Task.team_uuid == team_uuid)

        if assignee_uuid is not None:
            conditions.append(Task.assignee_uuid == assignee_uuid)

        stmt = select(Task.status, func.count(Task.uuid))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.group_by(Task.status)

        result = await self._session.execute(stmt)

        # Инициализируем все статусы нулями
        counts = {status: 0 for status in StatusEnum}

        # Заполняем реальными значениями
        for status, count in result.all():
            counts[status] = count

        return counts
