import asyncio
import os
from datetime import date
from typing import (
    AsyncGenerator,
    Generator,
)
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.pool import NullPool

from core.config import settings
from core.dependencies.depends import get_session
from core.interfaces import UUIDGenerator
from core.models.base import Base
from core.providers import UUIDGeneratorProvider
from main import create_app
from users.interfaces import PasswordHasher
from users.models import (
    GenderEnum,
    RoleEnum,
    User,
)
from users.providers import BcryptPasswordHasherProvider

TEST_DB_URL = settings.test_db_config.url


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """event loop для всей сессии тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Создание движка БД"""
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Создаем сессию БД для каждого теста"""
    LocalSession = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    async with LocalSession() as session:
        transaction = await session.begin()

        yield session

        await transaction.rollback()


@pytest.fixture
def app() -> FastAPI:
    """Создание приложения"""
    created_app = create_app()
    return created_app


@pytest_asyncio.fixture
async def client(
    app: FastAPI,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Создаем тестовый HTTP клиент с подменной БД"""

    def get_test_session() -> AsyncSession:
        return db_session

    app.dependency_overrides[get_session] = get_test_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def password_hasher() -> BcryptPasswordHasherProvider:
    """Хешер паролей для тестов"""
    return BcryptPasswordHasherProvider(rounds=4)


@pytest.fixture
def uuid_generator() -> UUIDGeneratorProvider:
    """Генератор UUID для тестов"""
    return UUIDGeneratorProvider()


# ================ ФИКСТУРЫ ПОЛЬЗОВАТЕЛЕЙ ================


@pytest_asyncio.fixture
async def admin_user(
    db_session: AsyncSession,
    password_hasher: PasswordHasher,
    uuid_generator: UUIDGenerator,
) -> User:
    """Тестовый админ"""

    admin = User(
        uuid=uuid_generator(),
        email="admin@example.com",
        password=password_hasher.hash_password("UserAdmin123!"),
        name="Admin",
        surname="User",
        gender=GenderEnum.MALE,
        birth_date=date(1990, 1, 1),
        role=RoleEnum.ADMIN,
        is_active=True,
        is_verified=True,
    )

    db_session.add(admin)
    await db_session.flush()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def manager_user(
    db_session: AsyncSession,
    password_hasher: PasswordHasher,
    uuid_generator: UUIDGenerator,
) -> User:
    """Тестовый менеджер"""

    manager = User(
        uuid=uuid_generator(),
        email="manager@example.com",
        password=password_hasher.hash_password("UserManager123!"),
        name="Manager",
        surname="User",
        gender=GenderEnum.FEMALE,
        birth_date=date(1995, 1, 1),
        role=RoleEnum.MANAGER,
        is_active=True,
        is_verified=True,
    )

    db_session.add(manager)
    await db_session.flush()
    await db_session.refresh(manager)

    return manager


@pytest_asyncio.fixture
async def employee_user(
    db_session: AsyncSession,
    password_hasher: PasswordHasher,
    uuid_generator: UUIDGenerator,
) -> User:
    """Тестовый работник"""

    employee = User(
        uuid=uuid_generator(),
        email="employee@example.com",
        password=password_hasher.hash_password("UserEmployee123!"),
        name="Employee",
        surname="User",
        gender=GenderEnum.MALE,
        birth_date=date(1993, 1, 1),
        role=RoleEnum.EMPLOYEE,
        is_active=True,
        is_verified=True,
    )

    db_session.add(employee)
    await db_session.flush()
    await db_session.refresh(employee)

    return employee


# ================ ФИКСТУРЫ ПОЛЬЗОВАТЕЛЕЙ ================
async def authenticated_client(
    client: AsyncClient,
    admin_user: User,
) -> AsyncClient:
    """Клиент с авторизованным админом"""

    login_data = {"email": admin_user.email, "password": "AdminPassword123!"}

    response = await client.post(
        "api/auth/login",
        json=login_data,
    )
    assert response.status_code == 200

    tokens = response.json()
    access_token = tokens["access_token"]

    client.headers.update({"Authorization": f"Bearer {access_token}"})

    return client


@pytest.fixture
def sample_user_data() -> dict[str, str]:
    """Данные для создания тестового пользователя"""
    return {
        "email": "newuser@test.com",
        "name": "New",
        "surname": "User",
        "gender": "Man",
        "birth_date": "1992-01-03",
        "password": "NewUserPassword123!",
    }
