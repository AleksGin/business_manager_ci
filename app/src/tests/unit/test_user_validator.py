from datetime import date
from unittest.mock import AsyncMock

import pytest
from freezegun import freeze_time

from src.core.providers import UUIDGeneratorProvider
from src.users.interfaces import (
    UserRepository,
    UserValidator,
)
from src.users.providers import UserValidatorProvider


@pytest.mark.unit
class TestUserValidatorProvider:
    """Тесты для UserValidatorProvider"""

    @pytest.fixture
    def mock_user_repo(self) -> AsyncMock:
        """Мок UserRepository"""
        repo = AsyncMock(spec=UserRepository)
        return repo

    @pytest.fixture
    def validator(self, mock_user_repo: AsyncMock) -> UserValidator:
        return UserValidatorProvider(mock_user_repo)

    # ================= Тесты для validate_age =================

    @freeze_time("2025-06-15")
    def test_validate_age_exactly_16_years_old(self, validator: UserValidator) -> None:
        """Тест: возраст ровно 16 лет - валиден"""
        birth_date = date(2009, 6, 15)

        result = validator.validate_age(birth_date=birth_date)

        assert result is True

    @freeze_time("2025-06-15")
    def test_validate_age_under_16_invalid(self, validator: UserValidator) -> None:
        """Тест: возраст меньше 16 лет - невалиден"""
        birth_date = date(2015, 6, 15)

        result = validator.validate_age(birth_date=birth_date)

        assert result is False

    @freeze_time("2025-06-15")
    def test_validate_age_over_16_valid(self, validator: UserValidator) -> None:
        """Тест: возраст больше 16 - валиден"""
        birth_date = date(2005, 6, 15)

        result = validator.validate_age(birth_date=birth_date)

        assert result is True

    # ================= Тесты для validate_password_strength =================

    def test_strength_password_valid(self, validator: UserValidator) -> None:
        """Тест: валиданый пароль"""

        test_password = "TestPsword195!"

        result = validator.validate_password_strength(test_password)

        assert result is True

    def test_short_password_invalid(self, validator: UserValidator) -> None:
        """Тест: короткий пароль (Меньше 10 символов)"""

        test_password = "Sh0rt!"

        result = validator.validate_password_strength(test_password)

        assert result is False

    def test_length_over_password_invalid(self, validator: UserValidator) -> None:
        """Тест: длинный пароль (больше 128 символов)"""

        test_password = "A1!" + "a" * 126

        result = validator.validate_password_strength(test_password)

        assert result is False

    def test_password_no_uppercase_invalid(self, validator: UserValidator) -> None:
        """Тест: пароль без заглавных букв"""

        test_password = "withoutupper0!"

        result = validator.validate_password_strength(test_password)

        assert result is False

    def test_password_no_lowercase_invalid(self, validator: UserValidator) -> None:
        """Тест: пароль без строчных букв"""

        test_password = "WITHOUTLOWER0!"

        result = validator.validate_password_strength(test_password)

        assert result is False

    def test_password_no_digits_invalid(self, validator: UserValidator) -> None:
        """Тест: пароль без цифр"""

        test_password = "WITHOUTdigits!"

        result = validator.validate_password_strength(test_password)

        assert result is False

    def test_password_no_special_symbol_invalid(self, validator: UserValidator) -> None:
        """Тест: пароль без специального символа"""

        test_password = "WithoutSpecial149"

        result = validator.validate_password_strength(test_password)

        assert result is False

    @pytest.mark.parametrize(
        "password, reason",
        [
            ("Password123", "contains 123"),
            ("Passwordabc!1", "contains abc"),
            ("Passwordqwe!1", "contains qwe"),
        ],
    )
    def test_password_sequential_chars_invalid(
        self,
        password: str,
        reason: str,
        validator: UserValidator,
    ) -> None:
        """Тест: пароль с последовательными символами"""
        result = validator.validate_password_strength(password)

        assert result is False

    @pytest.mark.parametrize(
        "password, reason",
        [
            ("Passsw0rd!2", "contains sss"),
            ("Rrrrepea!294", "contains rrr"),
            ("111aaaBBB!03", "contains [111, aaa, BBB]"),
        ],
    )
    def test_password_repeated_chars_invalid(
        self,
        password: str,
        reason: str,
        validator: UserValidator,
    ) -> None:
        """Тест: пароль с повторяющимися символами"""
        result = validator.validate_password_strength(password)

        assert result is False

    # ================= Тесты для validate_email_unique =================

    @pytest.mark.asyncio
    async def test_email_unique_new_email_valid(
        self,
        validator: UserValidator,
        mock_user_repo: AsyncMock,
    ) -> None:
        """Тест: новый email"""

        mock_user_repo.get_by_email.return_value = None

        result = await validator.validate_email_unique("new@example.com")

        assert result is True

        mock_user_repo.get_by_email.assert_called_once_with("new@example.com")

    @pytest.mark.asyncio
    async def test_email_unique_existing_email_invalid(
        self,
        validator: UserValidator,
        mock_user_repo: AsyncMock,
    ):
        """Тест: email занят"""

        existing_user = AsyncMock()
        existing_user.uuid = "existing-user-uuid"
        existing_user.email = "existing@test.com"

        mock_user_repo.get_by_email.return_value = existing_user

        result = await validator.validate_email_unique("existing@test.com")

        assert result is False

        mock_user_repo.get_by_email.assert_called_once_with("existing@test.com")

    @pytest.mark.asyncio
    async def test_email_unique_with_exclude_same_user_valid(
        self,
        validator: UserValidator,
        mock_user_repo: AsyncMock,
        uuid_generator: UUIDGeneratorProvider,
    ) -> None:
        """Тест: пользователь обновляет свой профиль"""

        user_uuid = uuid_generator()

        existing_user = AsyncMock()
        existing_user.uuid = user_uuid
        existing_user.email = "current@test.com"

        mock_user_repo.get_by_email.return_value = existing_user

        result = await validator.validate_email_unique(
            "current@test.com",
            user_uuid,
        )

        assert result is True

        mock_user_repo.get_by_email.assert_awaited_once_with(
            "current@test.com",
        )
