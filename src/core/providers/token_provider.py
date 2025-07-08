from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.interfaces.auth import TokenRepository
from core.models.user_token import (
    TokenType,
    UserToken,
)


class TokenRepositoryProvider(TokenRepository):
    """Имплементация TokenRepository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_token(
        self,
        user_uuid: UUID,
        token_hash: str,
        token_type: TokenType,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserToken:
        """Создать новый токен"""
        token = UserToken(
            user_uuid=user_uuid,
            token_hash=token_hash,
            token_type=token_type,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
        )

        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def get_token_by_hash(
        self,
        token_hash: str,
        token_type: TokenType,
    ) -> Optional[UserToken]:
        """Найти токен по хешу и типу"""
        stmt = select(UserToken).where(
            and_(
                UserToken.token_hash == token_hash,
                UserToken.token_type == token_type,
                UserToken.is_active == True,  # noqa: E712
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_token(self, token: UserToken) -> bool:
        """Деактивировать токен"""

        token.is_active = False
        await self._session.flush()
        return True

    async def deactivate_user_tokens(
        self,
        user_uuid: UUID,
        token_type: TokenType,
    ) -> int:
        """Деактивировать все токены пользователя определенного типа"""
        stmt = select(UserToken).where(
            and_(
                UserToken.user_uuid == user_uuid,
                UserToken.token_type == token_type,
                UserToken.is_active == True,  # noqa: E712
            )
        )

        result = await self._session.execute(stmt)

        tokens = result.scalars().all()

        count = 0

        for token in tokens:
            token.is_active = False
            count += 1

        await self._session.flush()

        return count

    async def cleanup_expired_tokens(self) -> int:
        """Удалить все просроченные токены"""

        now = datetime.now()
        stmt = select(UserToken).where(UserToken.expires_at < now)
        result = await self._session.execute(stmt)

        expired_tokens = result.scalars().all()

        count = 0

        for token in expired_tokens:
            await self._session.delete(token)
            count += 1

        await self._session.flush()
        return count

    async def get_user_active_tokens(
        self,
        user_uuid: UUID,
        token_type: TokenType | None = None,
    ) -> List[UserToken]:
        """Получить активные токены пользователя"""
        conditions = [
            UserToken.user_uuid == user_uuid,
            UserToken.is_active == True,
            UserToken.expires_at > datetime.now(),
        ]

        if token_type:
            conditions.append(UserToken.token_type == token_type)

        stmt = select(UserToken).where(and_(*conditions))
        stmt = stmt.order_by(UserToken.created_at.desc())

        result = await self._session.execute(stmt)

        return list(result.scalars().all())

    async def rotate_refresh_token(
        self,
        old_token_hash: str,
        new_token_hash: str,
        new_expires_at: datetime,
        user_uuid: UUID,
    ) -> Optional[UserToken]:
        """
        Заменить старый refresh токен на новый

        Args:
            old_token_hash: Хэш старого токена
            new_token_hash: Хэш нового токена
            new_expires_at: Время истечения нового токена
            user_uuid: UUID пользователя для проверки


        Returns:
            Новый токен или None, если старый не найден
        """

        # Найти старый токен
        old_token = await self.get_token_by_hash(
            old_token_hash,
            TokenType.REFRESH,
        )

        if not old_token or old_token.user_uuid != user_uuid:
            return None

        # Деактивировать старый
        await self.deactivate_token(old_token)

        # Создать новый
        new_token = await self.create_token(
            user_uuid=user_uuid,
            token_hash=new_token_hash,
            token_type=TokenType.REFRESH,
            expires_at=new_expires_at,
            ip_address=old_token.ip_address,
            user_agent=old_token.user_agent,
        )

        return new_token

    async def revoke_all_user_sessions(self, user_uuid: UUID) -> int:
        """Отозвать все сессии пользователя"""
        return await self.deactivate_user_tokens(
            user_uuid,
            TokenType.REFRESH,
        )
