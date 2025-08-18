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

from users.interfaces import UserRepository
from users.models import (
    RoleEnum,
    User,
)


class UserCRUD(UserRepository):
    """Имплементация UserRepository"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(self, user: User) -> User:
        """Создание нового пользователя"""
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_uuid(self, user_uuid: UUID) -> Optional[User]:
        """Получение пользователя по UUID"""
        stmt = select(User).where(User.uuid == user_uuid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, user_email: str) -> Optional[User]:
        """Получение пользователя по Email"""
        stmt = select(User).where(User.email == user_email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_role(
        self,
        role: RoleEnum,
        team_uuid: UUID | None = None,
    ) -> List[User]:
        """Получение пользователя по роли (опционально: в команде - team_uuid)"""

        stmt = select(User).where(User.role == role)

        if team_uuid is not None:
            stmt = stmt.where(User.team_uuid == team_uuid)

        stmt = stmt.order_by(User.created_at)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_user(self, user: User) -> User:
        """Обновление пользователя"""
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def delete_user(self, user_uuid: UUID) -> bool:
        """Удаление пользователя"""
        user = await self.get_by_uuid(user_uuid)

        if not user:
            return False

        await self._session.delete(user)
        await self._session.flush()
        return True

    async def list_users(
        self,
        limit: int = 50,
        offset: int = 0,
        team_uuid: UUID | None = None,
    ) -> List[User]:
        """Получить список пользователей с пагинацией и фильтрацией по команде"""
        stmt = select(User)

        # Фильтрация по команде
        if team_uuid is not None:
            stmt = stmt.where(User.team_uuid == team_uuid)

        # Пагинация
        stmt = stmt.offset(offset).limit(limit)

        # Сортировка для предсказуемости
        stmt = stmt.order_by(User.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_members(self, team_uuid: UUID) -> List[User]:
        """Получить всех участников команды"""
        stmt = select(User).where(User.team_uuid == team_uuid)
        stmt = stmt.order_by(User.role, User.created_at)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_users_without_team(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[User]:
        """Получение всех пользователей без команды"""
        stmt = select(User).where(User.team_uuid.is_(None))
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(User.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search_users(
        self,
        query: str,
        team_uuid: UUID | None = None,
        exclude_team: bool = False,
        limit: int = 50,
    ) -> List[User]:
        """
        Поиск пользователей по имени, фамилии или email.

        Args:
            query: поисковая строка
            team_uuid: ограничить поиск определенной командой
            exclude_team: исключить пользователей из указанной команды
            limit: максимальное количество результатов
        """
        query_search_pattern = f"%{query.lower()}%"

        # Поиск по имени, фамилии или email (регистронезависимый)

        stmt = select(User).where(
            or_(
                User.name.ilike(query_search_pattern),
                User.surname.ilike(query_search_pattern),
                User.email.ilike(query_search_pattern),
            )
        )

        # Фильтрация по команде

        if team_uuid is not None:
            if exclude_team:
                stmt = stmt.where(User.team_uuid != team_uuid)
            else:
                stmt = stmt.where(User.team_uuid == team_uuid)

        stmt = stmt.limit(limit)
        stmt = stmt.order_by(User.name, User.surname)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_email(self, email: str) -> bool:
        """Проверить существование пользователя по почте"""

        stmt = select(exists().where(User.email == email))
        result = await self._session.execute(stmt)

        exists_result = result.scalar()
        return exists_result is True
