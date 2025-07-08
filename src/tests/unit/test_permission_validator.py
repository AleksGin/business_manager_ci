from unittest.mock import AsyncMock

import pytest

from core.interfaces import PermissionValidator
from core.providers import PermissionValidatorProvider
from teams.models import Team
from users.models import (
    RoleEnum,
    User,
)


@pytest.mark.unit
class TestPermissionValidator:
    """Unit тесты для PermissionValidator"""

    @pytest.fixture
    def permission_validator(self) -> PermissionValidator:
        return PermissionValidatorProvider()

    @pytest.fixture
    def admin_user(self) -> AsyncMock:
        """Мок админа"""
        user = AsyncMock(spec=User)
        user.uuid = "admin-uuid"
        user.role = RoleEnum.ADMIN
        user.team_uuid = "team-1"
        return user

    @pytest.fixture
    def employee_user(self) -> AsyncMock:
        """Мок работника"""
        user = AsyncMock(spec=User)
        user.uuid = "employee-uuid"
        user.role = RoleEnum.EMPLOYEE
        user.team_uuid = "team-1"
        return user

    @pytest.fixture
    def manager_user(self) -> AsyncMock:
        """Мок менеджера"""
        user = AsyncMock(spec=User)
        user.uuid = "manager-uuid"
        user.role = RoleEnum.MANAGER
        user.team_uuid = "team-1"
        return user

    @pytest.fixture
    def test_team(self) -> AsyncMock:
        """Мок команды"""
        team = AsyncMock(spec=Team)
        team.uuid = "team-1"
        team.owner_uuid = "admin-uuid"
        return team

    @pytest.mark.asyncio
    async def test_can_view_user_admin_can_view_anyone(
        self,
        permission_validator: PermissionValidator,
        admin_user,
        employee_user,
        manager_user,
    ) -> None:
        """Тест: админ может просматривать любого пользователя"""

        admin_for_employee = await permission_validator.can_view_user(
            admin_user,
            employee_user,
        )
        admin_for_manager = await permission_validator.can_view_user(
            admin_user,
            manager_user,
        )

        assert admin_for_employee is True
        assert admin_for_manager is True

    @pytest.mark.asyncio
    async def test_can_view_user_self_access(
        self,
        permission_validator: PermissionValidator,
        employee_user,
    ) -> None:
        """Тест: пользователь может просматривать себя"""

        result = await permission_validator.can_view_user(
            employee_user,
            employee_user,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_view_user_employee_cannot_view_other_team(
        self,
        permission_validator: PermissionValidator,
        employee_user,
    ) -> None:
        """Тест: пользователь не может просматривать пользователей из других команд"""

        other_user = AsyncMock(spec=User)
        other_user.uuid = "other-uuid"
        other_user.team_uuid = "other-team-uuid"

        result = await permission_validator.can_view_user(
            employee_user,
            other_user,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_can_assign_role_admin_can_assign(
        self,
        permission_validator: PermissionValidator,
        admin_user,
    ) -> None:
        """Тест: админ может назначать роли любым пользователям"""

        other_user = AsyncMock(spec=User)

        user_to_employee = await permission_validator.can_assign_role(
            actor=admin_user,
            target_user=other_user,
            new_role=str(RoleEnum.EMPLOYEE),
        )
        user_to_manager = await permission_validator.can_assign_role(
            actor=admin_user,
            target_user=other_user,
            new_role=str(RoleEnum.MANAGER),
        )

        assert user_to_employee is True
        assert user_to_manager is True

    @pytest.mark.asyncio
    async def test_can_assign_role_non_admin_cannot(
        self,
        permission_validator: PermissionValidator,
        employee_user,
    ) -> None:
        """Тест: обычный сотрудник не может назначать роли"""

        other_user = AsyncMock(spec=User)

        user_to_manager = await permission_validator.can_assign_role(
            actor=employee_user,
            target_user=other_user,
            new_role=str(RoleEnum.MANAGER),
        )

        user_to_admin = await permission_validator.can_assign_role(
            actor=employee_user,
            target_user=other_user,
            new_role=str(RoleEnum.ADMIN),
        )

        assert user_to_manager is False
        assert user_to_admin is False

    @pytest.mark.asyncio
    async def test_can_assign_role_manager_cannot_assign(
        self,
        permission_validator: PermissionValidator,
        manager_user,
    ) -> None:
        """Тест: менеджер не может назначать роли"""

        other_user = AsyncMock(spec=User)

        result = await permission_validator.can_assign_role(
            actor=manager_user,
            target_user=other_user,
            new_role=RoleEnum.ADMIN.value,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_can_delete_user_admin_can_delete(
        self,
        permission_validator: PermissionValidator,
        admin_user,
        employee_user,
        manager_user,
    ) -> None:
        """ "Тест: админ может удалять пользователей"""

        delete_employee = await permission_validator.can_delete_user(
            admin_user,
            employee_user,
        )

        delete_manager = await permission_validator.can_delete_user(
            admin_user,
            manager_user,
        )

        assert delete_employee is True
        assert delete_manager is True

    @pytest.mark.parametrize(
        "fixture",
        [
            "admin_user",
            "employee_user",
            "manager_user",
        ],
    )
    @pytest.mark.asyncio
    async def test_can_delete_user_cannot_delete_self(
        self,
        permission_validator: PermissionValidator,
        request,
        fixture: str,
    ) -> None:
        """Тест: никто не может удалить сам себя"""

        user = request.getfixturevalue(fixture)

        result = await permission_validator.can_delete_user(
            user,
            user,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_can_create_team_employee_cannot(
        self,
        permission_validator: PermissionValidator,
        employee_user,
    ) -> None:
        """Тест: обычный сотрудник не можешь создавать команды"""

        result = await permission_validator.can_create_team(employee_user)

        assert result is False

    @pytest.mark.parametrize(
        "fixture",
        [
            "admin_user",
            "manager_user",
        ],
    )
    @pytest.mark.asyncio
    async def test_can_create_team_employee_admin_can(
        self,
        permission_validator: PermissionValidator,
        request,
        fixture: str,
    ) -> None:
        """Тест: и админ, и менеджер могут создавать команды"""

        user_or_manager = request.getfixturevalue(fixture)

        result = await permission_validator.can_create_team(user_or_manager)

        assert result is True

    @pytest.mark.asyncio
    async def test_can_update_team_admin_can_update_any_team(
        self,
        permission_validator: PermissionValidator,
        admin_user,
        test_team,
    ) -> None:
        """Тест: создатель команды может обновлять команду"""

        result = await permission_validator.can_update_team(
            actor=admin_user,
            team=test_team,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_update_team_owner_can_update_own_team(
        self,
        permission_validator: PermissionValidator,
        manager_user,
    ) -> None:
        """Тест: владелец может обновлять свою команду"""

        manager_team = AsyncMock(spec=Team)
        manager_team.uuid = "manager-team"
        manager_team.owner_uuid = manager_user.uuid

        result = await permission_validator.can_update_team(
            manager_user,
            manager_team,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_can_update_team_non_owner_cannot(
        self,
        permission_validator: PermissionValidator,
        manager_user,
    ) -> None:
        """Тест: менеджер другой команды не может обновлять другую команду"""

        other_manager = AsyncMock(spec=User)
        other_manager.uuid = "other-manager-uuid"

        other_team = AsyncMock(spec=Team)
        other_team.uuid = "other-team-uuid"
        other_team.owner_uuid = "other-manager-uuid"

        result = await permission_validator.can_update_team(
            manager_user,
            other_team,
        )
        
        assert result is False
