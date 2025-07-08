import pytest
from users.interfaces import PasswordHasher


@pytest.mark.unit
class TestBcryptPasswordHasher:
    """Тесты для BcryptPasswordHasherProvider"""

    def test_hash_password_creates_different_hashes(
        self,
        password_hasher: PasswordHasher,
    ) -> None:
        """Одинаковые пароли == разные хэши"""

        test_password = "TestPassword123!"

        hash1 = password_hasher.hash_password(test_password)
        hash2 = password_hasher.hash_password(test_password)

        assert hash1 != hash2
        assert len(hash1) > 0
        assert len(hash2) > 0

    def test_verify_password_success(self, password_hasher: PasswordHasher) -> None:
        """Тест: валидный пароль проверяется по хешу"""

        test_password = "TestPassword123!"

        hashed_passowrd = password_hasher.hash_password(test_password)

        assert (
            password_hasher.verify_password_by_hash(
                test_password,
                hashed_passowrd,
            )
            is True
        )

    def test_verify_invalid_hash_format(self, password_hasher: PasswordHasher) -> None:
        """Тест: неверный формат хэша"""
        test_password = "TestPassword123!"
        invalid_hash = "invalid_hash"

        assert (
            password_hasher.verify_password_by_hash(
                test_password,
                invalid_hash,
            )
            is False
        )
