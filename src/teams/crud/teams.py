from typing import (
    List,
    Optional,
)
from uuid import UUID

from sqlalchemy import (
    exists,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from teams.interfaces.interfaces import TeamRepository
from teams.models import Team


class TeamCRUD(TeamRepository):
    """Имплементация TeamRepository"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_team(self, team: Team) -> Team:
        """Создать новую команду"""
        self._session.add(team)
        await self._session.flush()
        await self._session.refresh(team)
        return team

    async def get_by_uuid(self, team_uuid: UUID) -> Optional[Team]:
        """Получить команду по UUID"""
        stmt = select(Team).where(Team.uuid == team_uuid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Team]:
        """Получить команду по названию"""
        stmt = select(Team).where(Team.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_team(self, team: Team) -> Team:
        """Обновить команду"""
        await self._session.flush()
        await self._session.refresh(team)
        return team

    async def delete_team(self, team_uuid: UUID) -> bool:
        """Удалить команду"""
        team = await self.get_by_uuid(team_uuid)

        if not team:
            return False

        await self._session.delete(team)
        await self._session.flush()
        return True

    async def get_user_teams(self, user_uuid: UUID) -> List[Team]:
        """Получить команды, где пользователь является владельцем"""
        stmt = select(Team).where(Team.owner_uuid == user_uuid)
        stmt = stmt.order_by(Team.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_teams(
        self,
        limit: int = 50,
        offset: int = 0,
        owner_uuid: Optional[UUID] = None,
    ) -> List[Team]:
        """Получить список команд с пагинацией и фильтрацией"""
        stmt = select(Team)

        # Фильтрация по владельцу
        if owner_uuid is not None:
            stmt = stmt.where(Team.owner_uuid == owner_uuid)

        # Пагинация
        stmt = stmt.offset(offset).limit(limit)

        # Сортировка
        stmt = stmt.order_by(Team.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_name(self, name: str) -> bool:
        """Проверить существование команды по названию"""
        stmt = select(exists().where(Team.name == name))
        result = await self._session.execute(stmt)

        exists_result = result.scalar()
        return exists_result is True

    async def get_team_with_members(self, team_uuid: UUID) -> Optional[Team]:
        """Получить команду с загруженными участниками"""
        stmt = select(Team).where(Team.uuid == team_uuid)
        stmt = stmt.options(
            selectinload(Team.members),  # Загружаем участников
            selectinload(Team.owner),  # Загружаем владельца
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_teams(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Team]:
        """Поиск команд по названию или описанию"""
        search_pattern = f"%{query.lower()}%"

        stmt = select(Team).where(
            or_(
                Team.name.ilike(search_pattern),
                Team.description.ilike(search_pattern),
            )
        )

        stmt = stmt.limit(limit)
        stmt = stmt.order_by(Team.name)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
