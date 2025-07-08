from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
)
from uuid import UUID

from core.models.user_token import (
    TokenType,
    UserToken,
)


class JWTProviderInterface(Protocol):
    """Интерфейс для работы с JWT токенами"""

    def create_access_token(
        self,
        user_uuid: UUID,
        user_tole: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Создать Access JWT токен"""
        ...

    def create_refresh_token(self) -> str:
        """Создать Refresh токен"""
        ...

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Проверить и декодировать Access токен"""
        ...

    def get_user_from_token(self, token: str) -> Optional[UUID]:
        """Извлечь UUID пользователя из токена"""
        ...

    def get_user_role_from_token(self, token: str) -> Optional[str]:
        """Извлечь роль пользователя из токена"""
        ...

    def hash_refresh_token(self, refresh_token: str) -> str:
        """Захешировать refresh токен для безопасного хранения в БД"""
        ...

    def create_token_pair(
        self,
        user_uuid: UUID,
        user_role: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Создать пару токенов (access + refresh)"""
        ...

    def get_refresh_token_expires_at(self) -> datetime:
        """Получить дату истечения refresh токена"""
        ...

    def create_verification_token(self, purpose: str = "email_verification") -> str:
        """Создать токен для верификации (email, password reset)"""
        ...

    def is_token_expired(self, token: str) -> bool:
        """Проверить истек ли access токен"""
        ...


class TokenRepository(Protocol):
    """Интерфейс для работы с пользовательскими токенами в БД"""

    async def create_token(
        self,
        user_uuid: UUID,
        token_hash: str,
        token_type: TokenType,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserToken:
        """Создать новый токен"""
        ...

    async def get_token_by_hash(
        self,
        token_hash: str,
        token_type: TokenType,
    ) -> Optional[UserToken]:
        """Найти токен по хэшу или типу"""
        ...

    async def deactivate_token(self, token: UserToken) -> bool:
        """Деактивировать токен"""
        ...

    async def deactivate_user_tokens(
        self, user_uuid: UUID, token_type: TokenType
    ) -> int:
        """Деактивировать все токены пользователя определенного типа"""
        ...

    async def cleanup_expired_tokens(self) -> int:
        """Удалить все просроченные токены"""
        ...

    async def get_user_active_tokens(
        self,
        user_uuid: UUID,
        token_type: Optional[TokenType] = None,
    ) -> List[UserToken]:
        """Получить активные токены пользователя"""
        ...

    async def rotate_refresh_token(
        self,
        old_token_hash: str,
        new_token_hash: str,
        new_expires_at: datetime,
        user_uuid: UUID,
    ) -> Optional[UserToken]:
        """Заменить старый refresh токен на новый"""
        ...

    async def revoke_all_user_sessions(self, user_uuid: UUID) -> int:
        """Отозвать все сессии пользователя"""
        ...
