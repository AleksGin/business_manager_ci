from datetime import (
    datetime,
    timedelta,
)
from uuid import UUID

from core.interfaces import (
    DBSession,
    JWTProviderInterface,
    TokenRepository,
)
from core.models.user_token import TokenType
from users.interfaces.interfaces import (
    PasswordHasher,
    UserActivationManager,
    UserRepository,
    UserValidator,
)


class UserActivationManagerProvider(UserActivationManager):
    """Имплементация UserActivationManager с хранением токенов в БД"""

    def __init__(
        self,
        user_repo: UserRepository,
        jwt_provider: JWTProviderInterface,
        token_repository: TokenRepository,
        password_hasher: PasswordHasher,
        db_session: DBSession,
        user_validator: UserValidator,
        verification_token_ttl_hours: int = 24,
        reset_token_ttl_hours: int = 1,
    ) -> None:
        """
        Args:
            user_repo: Репозиторий пользоватеелй
            jwt_provider: Сервис для работы с токенами
            token_repository: Репозиторий токенов
            verification_token_ttl_hours: Время жизни токенов верификации (24 ч)
            reset_token_ttl_hours: Время жизни токенов сброса пароля (1 ч)
        """
        self._user_repo = user_repo
        self._jwt_provider = jwt_provider
        self._token_repository = token_repository
        self._password_hasher = password_hasher
        self._db_session = db_session
        self._user_validator = user_validator
        self._verification_ttl = timedelta(hours=verification_token_ttl_hours)
        self._reset_ttl = timedelta(hours=reset_token_ttl_hours)

    async def activate_user(
        self,
        user_uuid: UUID,
        activated_by: UUID,
    ) -> bool:
        """Активировать пользователя"""
        user = await self._user_repo.get_by_uuid(user_uuid)
        if not user:
            return False

        user.is_active = True
        await self._user_repo.update_user(user)
        return True

    async def deactivate_user(
        self,
        user_uuid: UUID,
        deactivated_by: UUID,
    ) -> bool:
        """Деактивировать пользователя"""
        user = await self._user_repo.get_by_uuid(user_uuid)
        if not user:
            return False

        user.is_active = False
        await self._user_repo.update_user(user)
        return True

    async def verify_user_email(
        self,
        user_uuid: UUID,
        verification_token: str,
    ) -> bool:
        """Подтвердить email пользователя с помощью токена"""

        # Хешируем токен для поиска в БД
        token_hash = self._jwt_provider.hash_refresh_token(verification_token)

        # Ищем токен в БД
        token_record = await self._token_repository.get_token_by_hash(
            token_hash,
            TokenType.EMAIL_VERIFICATION,
        )

        # Проверяем соответствие пользователя
        if not token_record or not token_record.is_valid():
            return False

        # Подтверждаем email
        user = await self._user_repo.get_by_uuid(user_uuid)

        if not user:
            return False

        user.is_verified = True
        await self._user_repo.update_user(user)

        # Деактивируем использованный токен
        await self._token_repository.deactivate_token(token_record)
        return True

    async def generate_verification_token(self, user_uuid: UUID) -> str:
        """Создать токен для подтверждения email"""

        # Деактивируем старые токены верификации
        await self._token_repository.deactivate_user_tokens(
            user_uuid,
            TokenType.EMAIL_VERIFICATION,
        )

        # Генерируем новый токен
        token = self._jwt_provider.create_verification_token("email_verification")
        token_hash = self._jwt_provider.hash_refresh_token(token)

        # Сохраняем в БД
        await self._token_repository.create_token(
            user_uuid=user_uuid,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=datetime.now() + self._verification_ttl,
        )

        return token

    async def reset_password_request(self, email: str) -> str:
        """Создать запрос на сброс пароля"""

        # Проверяем существование пользователя

        user = await self._user_repo.get_by_email(email)
        if not user:
            # Генерируем фейковый токен для защиты от перебора email
            return self._jwt_provider.create_verification_token("fake")

        # Деактивируем старые токены сброса
        await self._token_repository.deactivate_user_tokens(
            user.uuid,
            TokenType.PASSWORD_RESET,
        )

        # Генерируем новый токен
        token = self._jwt_provider.create_verification_token("password reset")
        token_hash = self._jwt_provider.hash_refresh_token(token)

        # Сохраняем в БД с коротким TTL
        await self._token_repository.create_token(
            user_uuid=user.uuid,
            token_hash=token_hash,
            token_type=TokenType.PASSWORD_RESET,
            expires_at=datetime.now() + self._reset_ttl,
        )

        return token

    async def reset_password_confirm(
        self,
        token: str,
        new_password: str,
    ) -> bool:
        """Подтвердить сброс пароля и установить новый"""
        
        # Валидация пароля
        if not self._user_validator.validate_password_strength(new_password):
            raise ValueError("Пароль не соответствует требованиям безопасности")

        # Хешируем токен для поиска
        token_hash = self._jwt_provider.hash_refresh_token(token)

        # Ищем токен в БД
        token_record = await self._token_repository.get_token_by_hash(
            token_hash,
            TokenType.PASSWORD_RESET,
        )

        if not token_record or not token_record.is_valid():
            return False

        # Получаем пользователя
        user = await self._user_repo.get_by_uuid(token_record.user_uuid)
        if not user:
            return False

        # Устанавливаем новый пароль
        new_hashed_password = self._password_hasher.hash_password(new_password)

        user.password = new_hashed_password
        await self._user_repo.update_user(user)

        # Деактивируем использованный токен
        await self._token_repository.deactivate_token(token_record)

        # Отзываем все сессии пользователя для безопасности
        await self._token_repository.revoke_all_user_sessions(user.uuid)

        return True
