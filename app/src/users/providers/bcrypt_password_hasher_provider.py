import bcrypt

from src.core.config import settings
from src.users.interfaces import PasswordHasher


class BcryptPasswordHasherProvider(PasswordHasher):
    """Имплементация PasswordHasher (используется bcrypt)"""

    def __init__(
        self,
        rounds: int = settings.bcrypt_settings.default_rounds_value,
    ) -> None:
        """
        Args:
            rounds: Количество раундов хэширования (по умолчанию 12)
        """
        self._rounds = rounds

    def hash_password(self, password: str) -> str:
        """Захэшировать пароль с использованием bcrypt"""
        # Преоброзование пароля в bytes
        password_bytes = password.encode("utf-8")

        # Генерируем соль и хэшируем
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)

        # Возвращаем строку
        return hashed.decode("utf-8")

    def verify_password_by_hash(
        self,
        password: str,
        hashed_password: str,
    ) -> bool:
        """Проверить соответствие пароля по хэшу"""
        try:
            # Преобразуем в bytes
            password_bytes = password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")

            # Проверяем соответствие
            return bcrypt.checkpw(password_bytes, hashed_bytes)

        except (ValueError, TypeError):
            # Неверный формат или другие ошибки
            return False
