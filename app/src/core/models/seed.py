from datetime import date

from sqlalchemy import select
from src.core.config import settings
from src.core.models import all_models
from src.core.models.db_helper import DbHelper
from src.users.models.user import (
    GenderEnum,
    RoleEnum,
    User,
)
from src.users.providers import BcryptPasswordHasherProvider


async def create_default_users():
    hasher = BcryptPasswordHasherProvider()

    async for session in DbHelper.session_getter():
        emails = ["employee@test.com", "manager@test.com", "admin@test.com"]
        existing_users = (
            (await session.execute(select(User).where(User.email.in_(emails))))
            .scalars()
            .all()
        )
        existing_emails = {u.email for u in existing_users}

        users_to_add = []
        if "employee@test.com" not in existing_emails:
            users_to_add.append(
                User(
                    email="employee@test.com",
                    password=hasher.hash_password(
                        settings.test_user_config.employee_password
                    ),
                    name=RoleEnum.EMPLOYEE,
                    surname="Test",
                    gender=GenderEnum.MALE,
                    birth_date=date(1990, 1, 1),
                    role=RoleEnum.EMPLOYEE,
                )
            )
        if "manager@test.com" not in existing_emails:
            users_to_add.append(
                User(
                    email="manager@test.com",
                    password=hasher.hash_password(
                        settings.test_user_config.manager_password
                    ),
                    name=RoleEnum.MANAGER,
                    surname="Test",
                    gender=GenderEnum.MALE,
                    birth_date=date(1990, 1, 1),
                    role=RoleEnum.MANAGER,
                )
            )
        if "admin@test.com" not in existing_emails:
            users_to_add.append(
                User(
                    email="admin@test.com",
                    password=hasher.hash_password(
                        settings.test_user_config.admin_password
                    ),
                    name=RoleEnum.ADMIN,
                    surname="Test",
                    gender=GenderEnum.MALE,
                    birth_date=date(1990, 1, 1),
                    role=RoleEnum.ADMIN,
                )
            )

        session.add_all(users_to_add)
        await session.commit()
