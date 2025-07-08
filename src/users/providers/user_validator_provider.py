import re
from datetime import date
from uuid import UUID

from users.interfaces import (
    UserRepository,
    UserValidator,
)


class UserValidatorProvider(UserValidator):
    """Имплементация UserValidator: бизнес-валидация пользователей"""

    def __init__(self, user_repo: UserRepository) -> None:
        """
        Args:
            user_repo: UserRepository - для проверки данных в БД
        """
        self._user_repo = user_repo

    async def validate_email_unique(
        self,
        email: str,
        exclude_uuid: UUID | None = None,
    ) -> bool:
        """
        Проверить уникальность email

        Args:
            email: проверяемый email
            exclude_uuid: исключить пользователя с этим UUID при проверке

        """

        # Проверяем существование пользователя
        existing_user = await self._user_repo.get_by_email(email)

        # Если пользователь нет - email уникален
        if not existing_user:
            return True

        # Если указан exclude_uuid и это тот же пользователь
        if exclude_uuid and existing_user.uuid == exclude_uuid:
            return True

        # В остальных случаях - не уникален
        return False

    def validate_age(self, birth_date: date) -> bool:
        """Проверить соответствие возраста минимальным требованиям"""
        today = date.today()

        # Вычисляем возраст
        age = today.year - birth_date.year

        # Корректируем, если день рождения еще не наступил в этом году
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1

        # Минимальный возраст 16 лет
        return age >= 16

    def validate_password_strength(self, password: str) -> bool:
        """Проверить соответствие пароля требованиям безопасности"""

        # Минимальная длина
        if len(password) < 10:
            return False

        # Максимальная длина
        if len(password) > 128:
            return False

        # Должна быть хотя бы одна заглавная буква
        if not re.search(r"[A-Z]", password):
            return False

        # Должна быть хотя бы одна строчная буква
        if not re.search(r"[a-z]", password):
            return False

        # Должна быть хотя бы одна цифра
        if not re.search(r"[0-9]", password):
            return False

        # Должен быть хотя бы один специальный символ
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\];\'\\`~]', password):
            return False

        # Проверка на последовательности
        if self._has_sequential_chars(password):
            return False

        # Проверка на повторяющиеся символы
        if self._has_repeated_chars(password):
            return False

        return True

    def _has_sequential_chars(self, password: str) -> bool:
        """Проверить наличие последовательных символов (123, abc, qwe)"""
        sequences = [
            "0123456789",
            "abcdefghijklmnopqrstuvwxyz",
            "qwertyuiopasdfghjklzxcvbnm",
        ]

        password_lower = password.lower()

        for sequence in sequences:
            # Проверяем последовательности длиной 3+ символа
            for i in range(len(sequence) - 2):
                subseq = sequence[i : i + 3]
                if subseq in password_lower:
                    return True
                # Проверяем обратную последовательность
                if subseq[::-1] in password_lower:
                    return True

        return False

    def _has_repeated_chars(self, password: str) -> bool:
        """Проверить наличие повторяющихся символов (aaa, 111)"""
        # Ищем 3+ одинаковых символа подряд
        for i in range(len(password) - 2):
            if password[i] == password[i + 1] == password[i + 2]:
                return True

        return False
