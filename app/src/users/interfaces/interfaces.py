from abc import abstractmethod
from datetime import date
from typing import (
    List,
    Optional,
    Protocol,
)
from uuid import UUID

from src.users.models import (
    RoleEnum,
    User,
)


class UserRepository(Protocol):
    """Интерфейс для работы с пользователями в хранилище данных"""

    async def create_user(self, user: User) -> User:
        """Создать нового пользователя в системе"""
        ...

    async def get_by_uuid(self, user_uuid: UUID) -> Optional[User]:
        """Получить пользователя по UUID. Возвращает None если не найден"""
        ...

    async def get_by_email(self, user_email: str) -> Optional[User]:
        """Получить пользователя по email. Возвращает None если не найден"""
        ...

    async def update_user(self, user: User) -> User:
        """Обновить данные существующего пользователя"""
        ...

    async def delete_user(self, user_uuid: UUID) -> bool:
        """Удалить пользователя. Возвращает True если удален успешно"""
        ...

    async def list_users(
        self,
        limit: int = 50,
        offset: int = 0,
        team_uuid: Optional[UUID] = None,
    ) -> List[User]:
        """Получить список пользователей с пагинацией и фильтрацией по команде"""
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Проверить существование пользователя с указанным email"""
        ...

    @abstractmethod
    async def get_by_role(
        self,
        role: RoleEnum,
        team_uuid: Optional[UUID] = None,
    ) -> List[User]:
        """Получить пользователей по роли, опционально в конкретной команде"""
        ...

    @abstractmethod
    async def get_team_members(self, team_uuid: UUID) -> List[User]:
        """Получить всех участников указанной команды"""
        ...

    @abstractmethod
    async def get_users_without_team(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[User]:
        """Получить пользователей, не состоящих ни в одной команде"""
        ...

    @abstractmethod
    async def search_users(
        self,
        query: str,
        team_uuid: Optional[UUID] = None,
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
        ...


class PasswordHasher(Protocol):
    """Интерфейс для работы с хешированием и проверкой паролей"""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Захешировать пароль для безопасного хранения"""
        ...

    @abstractmethod
    def verify_password_by_hash(
        self,
        password: str,
        hashed_password: str,
    ) -> bool:
        """Проверить соответствие пароля его хешу"""
        ...


class UserValidator(Protocol):
    """Интерфейс для бизнес-валидации пользователей"""

    @abstractmethod
    async def validate_email_unique(
        self,
        email: str,
        exclude_uuid: Optional[UUID] = None,
    ) -> bool:
        """
        Проверить уникальность email адреса.

        Args:
            email: проверяемый email
            exclude_uuid: исключить пользователя с этим UUID из проверки
        """
        ...

    @abstractmethod
    def validate_age(self, birth_date: date) -> bool:
        """Проверить соответствие возраста минимальным требованиям (минимальное требование -- 16 лет)"""
        ...

    @abstractmethod
    def validate_password_strength(self, password: str) -> bool:
        """Проверить соответствие пароля требованиям безопасности"""
        ...


class UserActivationManager(Protocol):
    """Интерфейс для управления активацией и верификацией пользователей"""

    @abstractmethod
    async def activate_user(
        self,
        user_uuid: UUID,
        activated_by: UUID,
    ) -> bool:
        """
        Активировать пользователя (разрешить доступ к системе).

        Args:
            user_uuid: кого активируем
            activated_by: кто активирует
        """
        ...

    @abstractmethod
    async def deactivate_user(
        self,
        user_uuid: UUID,
        deactivated_by: UUID,
    ) -> bool:
        """
        Деактивировать пользователя (заблокировать доступ).

        Args:
            user_uuid: кого деактивируем
            deactivated_by: кто деактивирует
        """
        ...

    @abstractmethod
    async def verify_user_email(
        self,
        user_uuid: UUID,
        verification_token: str,
    ) -> bool:
        """
        Подтвердить email пользователя с помощью токена верификации.

        Args:
            user_uuid: чей email подтверждается
            verification_token: токен из письма подтверждения
        """
        ...

    @abstractmethod
    async def generate_verification_token(self, user_uuid: UUID) -> str:
        """
        Создать токен для подтверждения email.

        Returns:
            токен для отправки в письме подтверждения
        """
        ...

    @abstractmethod
    async def reset_password_request(self, email: str) -> str:
        """
        Создать запрос на сброс пароля.

        Args:
            email: email пользователя, запросившего сброс

        Returns:
            токен для сброса пароля
        """
        ...

    @abstractmethod
    async def reset_password_confirm(
        self,
        token: str,
        new_password: str,
    ) -> bool:
        """
        Подтвердить сброс пароля и установить новый.

        Args:
            token: токен из письма сброса пароля
            new_password: новый пароль пользователя
        """
        ...
