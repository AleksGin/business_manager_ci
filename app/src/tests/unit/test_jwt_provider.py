from uuid import uuid4

import pytest

from src.core.interfaces import JWTProviderInterface
from src.core.providers import JWTProvider


@pytest.mark.unit
class TestJWTProvider:
    """Unit тесты для JWTProvider"""

    @pytest.fixture
    def jwt_provider(self) -> JWTProviderInterface:
        """Фикстура для JWTProvider"""
        return JWTProvider(
            secret_key="test_secret_key_for_tests",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    def test_create_access_token_success(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: создание access токена"""

        user_uuid = uuid4()
        user_role = "ADMIN"

        token = jwt_provider.create_access_token(
            user_uuid,
            user_role,
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Декодирование токена

        payload = jwt_provider.verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_uuid)
        assert payload["role"] == user_role
        assert payload["type"] == "access"

    def test_create_refresh_token_returns_different_tokens(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: проверка, что разные refresh токены всегда разные"""

        token1 = jwt_provider.create_refresh_token()
        token2 = jwt_provider.create_refresh_token()

        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0

    def test_verify_access_token_invalid_token(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: токен невалиден"""

        result = jwt_provider.verify_access_token("invalid_token")

        assert result is None

    def test_get_user_from_token_success(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: извлечение UUID пользователя из токена"""

        user_uuid = uuid4()
        token = jwt_provider.create_access_token(
            user_uuid,
            "USER",
        )

        extracted_uuid = jwt_provider.get_user_from_token(token)

        assert extracted_uuid == user_uuid

    def test_get_user_from_invalid_token(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: получение UUID пользователя из невалидного токена"""

        extracted_uuid = jwt_provider.get_user_from_token("not_a_jwt_token")

        assert extracted_uuid is None

    def test_get_user_role_from_token_success(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: получение роли из токена"""

        user_uuid = uuid4()
        user_role = "ADMIN"

        token = jwt_provider.create_access_token(
            user_uuid,
            user_role,
        )

        extracted_role = jwt_provider.get_user_role_from_token(token)

        assert user_role == extracted_role

    def test_hash_refresh_token_same_input_same_ouput(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: одинаковый токен всегда дает одинаковый хэш"""

        refresh_token = "test_refresh_token_123"

        hash1 = jwt_provider.hash_refresh_token(refresh_token)
        hash2 = jwt_provider.hash_refresh_token(refresh_token)

        assert hash1 == hash2

    def test_create_token_pair_contains_both_tokens(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: создание пары токенов"""

        user_uuid = uuid4()
        user_role = "MANAGER"

        result = jwt_provider.create_token_pair(
            user_uuid,
            user_role,
        )
        assert len(result) > 0

        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result

        assert len(result["access_token"]) > 0
        assert len(result["refresh_token"]) > 0
        assert result["token_type"] == "Bearer"

        assert result["access_token"] != result["refresh_token"]

        payload = jwt_provider.verify_access_token(result["access_token"])

        assert payload is not None
        assert payload["sub"] == str(user_uuid)
        assert payload["role"] == user_role
        assert payload["type"] == "access"

    def test_is_token_expired_fresh_token(
        self,
        jwt_provider: JWTProviderInterface,
    ) -> None:
        """Тест: свежесозданный токен не должен быть истекшим"""

        user_uuid = uuid4()
        user_role = "EMPLOYEE"

        token = jwt_provider.create_access_token(
            user_uuid,
            user_role,
        )

        result = jwt_provider.is_token_expired(token)

        assert result is False

    def test_is_token_expired_old_token(self) -> None:
        """Тест: токен с истекшим сроком действия"""

        short_lived_provider = JWTProvider(
            secret_key="short-lived-provider-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=0,
        )

        user_uuid = uuid4()
        user_role = "ADMIN"

        token = short_lived_provider.create_access_token(
            user_uuid,
            user_role,
        )

        result = short_lived_provider.is_token_expired(token)

        assert result is True
