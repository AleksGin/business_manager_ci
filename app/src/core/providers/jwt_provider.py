import hashlib
import secrets
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
    Optional,
)
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from core.config import settings
from core.interfaces.auth import JWTProviderInterface


class JWTProvider(JWTProviderInterface):
    """Имплементация JWTProviderInterface"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """
        Args:
            secret_key: Секретный ключ для подписи токенов
            algorithm: Алгоритм шифрования (по умолчанию HS256)
            access_token_expire_minutes: Время жизни access токена в минутах
            refresh_token_expire_days: Время жизни refresh токена в днях
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_delta = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire_delta = timedelta(days=refresh_token_expire_days)

    def create_access_token(
        self,
        user_uuid: UUID,
        user_role: str,
        additional_claims: Dict[str, Any] | None = None,
    ) -> str:
        """
        Создать Access JWT токен

        Args:
            user_uuid: UUID пользователя
            user_tole: Роль пользователя
            additional_claims: Дополнительные данные для токена
        """

        now = datetime.now()
        expire = now + self.access_token_expire_delta

        payload = {
            "sub": str(user_uuid),
            "role": user_role,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": secrets.token_hex(16),
        }

        # Добавляем дополнительные данные если есть
        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload=payload,
            key=self.secret_key,
            algorithm=self.algorithm,
        )

    def create_refresh_token(self) -> str:
        """
        Создать Refresh токен

        Returns:
            Refresh токен (random string)
        """

        return secrets.token_urlsafe(64)

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Проверить и декодировать Access токен

        Args:
            token: JWT access токен

        Returns:
            Данные из токена или None, если токен невалидный
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            if payload.get("type") != "access":
                return None

            return payload

        except InvalidTokenError:
            return None

    def get_user_from_token(self, token: str) -> Optional[UUID]:
        """
        Получить пользователя из токена

        Args:
            token: JWT access токен

        Returns:
            UUID пользователя или None
        """
        payload = self.verify_access_token(token)
        if not payload:
            return None

        try:
            return UUID(payload["sub"])
        except (ValueError, KeyError):
            return None

    def get_user_role_from_token(self, token: str) -> Optional[str]:
        """
        Получить роль пользователя из токена

        Args:
            JWT access token

        Returns:
            Роль пользователя или None
        """

        payload = self.verify_access_token(token)

        if not payload:
            return None

        try:
            return payload.get("role")
        except (ValueError, KeyError):
            return None

    def hash_refresh_token(self, refresh_token: str) -> str:
        """
        Захешировать refresh токен для хранения в БД

        Args:
            refresh_token: Исходный refresh токен

        Returns:
            Хеш токена
        """

        return hashlib.sha256(refresh_token.encode()).hexdigest()

    def create_token_pair(
        self,
        user_uuid: UUID,
        user_role: str,
        additional_claims: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Создать пару токенов (access + refresh)

        Args:
            user_uuid: UUID пользователя
            user_role: Роль пользователя
            additional_claims: Дополнительные данные для access токена

        Returns:
            Словарь с токенами метаданными
        """
        access_token = self.create_access_token(
            user_uuid,
            user_role,
            additional_claims,
        )
        refresh_token = self.create_refresh_token()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": int(self.access_token_expire_delta.total_seconds()),
            "refresh_expires_in": int(self.refresh_token_expire_delta.total_seconds()),
        }

    def get_refresh_token_expires_at(self) -> datetime:
        """Получить дату истечения refresh токена"""
        return datetime.now() + self.refresh_token_expire_delta

    def create_verification_token(self, purpose: str = "email_verification") -> str:
        """
        Создать токен для верификации (email, password reset)

        Args:
            purpose: Назначение токена

        Returns:
            Случайный токен
        """
        return secrets.token_urlsafe(32)

    def is_token_expired(self, token: str) -> bool:
        """
        Проверить истек ли access токен

        Args:
            token: JWT access токен

        Returns:
            True, если токен истек
        """

        payload = self.verify_access_token(token)

        if not payload:
            return True

        exp = payload.get("exp")

        if not exp:
            return True

        return datetime.now().timestamp() > exp


# Глобальный экземпляр JWT сервиса
jwt_provider = JWTProvider(
    secret_key=settings.auth.secret_key,
    algorithm=settings.auth.algorithm,
    access_token_expire_minutes=settings.auth.access_token_expire_minutes,
    refresh_token_expire_days=settings.auth.refresh_token_expire_days,
)
