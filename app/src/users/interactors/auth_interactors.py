from typing import Optional
from uuid import UUID

from core.interfaces import (
    DBSession,
    PermissionValidator,
)
from users.interfaces import (
    PasswordHasher,
    UserActivationManager,
    UserRepository,
    UserValidator,
)
from users.models import User


class ChangePasswordInteractor:
    """Интерактор для смены пароля"""

    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher,
        user_validator: UserValidator,
        permission_validator: PermissionValidator,
        db_session: DBSession,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._user_validator = user_validator
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Сменить пароль пользователя"""

        try:
            # 1. Найти участника
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            target = await self._user_repo.get_by_uuid(target_uuid)

            if not actor:
                raise ValueError("Пользователь actor не найден")
            if not target:
                raise ValueError("Целевой пользователь не найден")

            # 2. Проверить права доступа (либо сам пользователь, либо админ)
            if actor.uuid != target.uuid:
                if not await self._permission_validator.is_system_admin(actor):
                    raise PermissionError("Нет прав для смены пароля")

            # 3. Проверить текущий пароль (если пользователь меняем сам)
            if actor.uuid == target.uuid:
                if not self._password_hasher.verify_password_by_hash(
                    current_password,
                    target.password,
                ):
                    raise ValueError("Неверный текущий пароль")

            # 4. Валидация нового пароля
            if not self._user_validator.validate_password_strength(new_password):
                raise ValueError(
                    "Новый пароль не соответствует требованиям безопасности"
                )

            # 5. Обновить пароль
            target.password = self._password_hasher.hash_password(new_password)

            await self._user_repo.update_user(target)
            await self._db_session.commit()

            return True

        except Exception:
            await self._db_session.rollback()
            raise


class AuthenticateUserInteractor:
    """Интерактор для аутентификации пользователя"""

    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def __call__(self, email: str, password: str) -> Optional[User]:
        """
        Аутентифицировать пользователя по email и паролю.

        Returns:
            User -- если аутентификация успешна, None -- если данные неверны
        """

        # 1. Найти пользователя
        user = await self._user_repo.get_by_email(email)
        if not user:
            return None

        # 2. Проверить статус активности
        if not user.is_active:
            raise ValueError("Аккаунт деактивирован")

        # 3. Проверить пароль
        if not self._password_hasher.verify_password_by_hash(password, user.password):
            return None

        return user


class RequestPasswordResetInteractor:
    """Запрос на сброс пароля (забыл пароль)"""

    def __init__(
        self,
        activation_manager: UserActivationManager,
        db_session: DBSession,
    ) -> None:
        self._activation_manager = activation_manager
        self._db_session = db_session

    async def __call__(self, email: str) -> str:
        """Запросить сброс пароля"""
        try:
            token = await self._activation_manager.reset_password_request(email)
            await self._db_session.commit()

            # TODO: Отправить email с токеном
            # await email_service.send_reset_password(email, token)

            return token

        except Exception:
            await self._db_session.rollback()
            raise


class ConfirmPasswordResetInteractor:
    """Подтверждение сброса пароля"""

    def __init__(
        self,
        activation_manager: UserActivationManager,
        db_session: DBSession,
    ) -> None:
        self._activation_manager = activation_manager
        self._db_session = db_session

    async def __call__(self, token: str, new_password: str) -> bool:
        """Установить новый пароль по токену"""
        try:
            result = await self._activation_manager.reset_password_confirm(
                token,
                new_password,
            )
            if result:
                await self._db_session.commit()
                return True
            else:
                raise ValueError("Недействительный или истекший токен")

        except Exception:
            await self._db_session.rollback()
            raise


class VerifyEmailInteractor:
    """Подтверждение email"""

    def __init__(
        self,
        activation_manager: UserActivationManager,
        db_session: DBSession,
    ) -> None:
        self._activation_manager = activation_manager
        self._db_session = db_session

    async def __call__(
        self,
        user_uuid: UUID,
        token: str,
    ) -> bool:
        """Подтвердить email пользователя"""
        try:
            result = await self._activation_manager.verify_user_email(
                user_uuid,
                token,
            )

            if result:
                await self._db_session.commit()
                return True
            else:
                raise ValueError("Недействительный или истекший токен")
        except Exception:
            await self._db_session.rollback()
            raise


class AdminActivateUserInteractor:
    """Активация/Деактивация пользователя администратором"""

    def __init__(
        self,
        activation_manager: UserActivationManager,
        permission_validator: PermissionValidator,
        user_repo: UserRepository,
        db_session: DBSession,
    ) -> None:
        self._activation_manager = activation_manager
        self._permission_validator = permission_validator
        self._user_repo = user_repo
        self._db_session = db_session

    async def activate(self, actor_uuid: UUID, target_uuid: UUID) -> bool:
        """Активировать пользователя"""
        try:
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            if not actor:
                raise ValueError("Администратор не найден")

            if not await self._permission_validator.is_system_admin(actor):
                raise PermissionError("Нет прав для активации пользователей")

            result = await self._activation_manager.activate_user(
                target_uuid,
                actor_uuid,
            )

            if result:
                await self._db_session.commit()
                return True
            else:
                raise ValueError("Пользователь не найден")

        except Exception:
            await self._db_session.rollback()
            raise

    async def deactivate(
        self,
        actor_uuid: UUID,
        target_uuid: UUID,
    ) -> bool:
        """Деактивировать пользователя"""
        try:
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            if not actor:
                raise ValueError("Администратор не найден")

            if not await self._permission_validator.is_system_admin(actor):
                raise PermissionError("Нет прав для деактивации пользователей")

            result = await self._activation_manager.deactivate_user(
                target_uuid,
                actor_uuid,
            )

            if result:
                await self._db_session.commit()
                return True
            else:
                raise ValueError("Пользователь не найден")

        except Exception:
            await self._db_session.rollback()
            raise
