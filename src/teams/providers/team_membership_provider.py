# teams/providers/team_membership_provider.py

from uuid import UUID

from core.interfaces import DBSession
from teams.interfaces import (
    TeamMembershipManager,
    TeamRepository,
)
from teams.interactors.team_membership_interactors import (
    AddTeamMemberInteractor,
    GenerateInviteCodeInteractor,
    JoinTeamByInviteCodeInteractor,
    RemoveTeamMemberInteractor,
    TransferOwnershipInteractor,
)
from users.interfaces import UserRepository


class TeamMembershipManagerProvider(TeamMembershipManager):
    """Провайдер для управления членством в командах"""

    def __init__(
        self,
        team_repo: TeamRepository,
        user_repo: UserRepository,
        db_session: DBSession,
    ) -> None:
        self._team_repo = team_repo
        self._user_repo = user_repo
        self._db_session = db_session

    async def add_user_to_team(
        self,
        user_uuid: UUID,
        team_uuid: UUID,
        added_by: UUID,
    ) -> bool:
        """Добавить пользователя в команду"""

        interactor = AddTeamMemberInteractor(
            team_repo=self._team_repo,
            user_repo=self._user_repo,
            permission_validator=None,  # Пока None
            db_session=self._db_session,
        )

        return await interactor(
            actor_uuid=added_by,
            team_uuid=team_uuid,
            user_uuid=user_uuid,
        )

    async def remove_user_from_team(
        self,
        user_uuid: UUID,
        team_uuid: UUID,
        removed_by: UUID,
    ) -> bool:
        """Удалить пользователя из команды"""

        interactor = RemoveTeamMemberInteractor(
            team_repo=self._team_repo,
            user_repo=self._user_repo,
            permission_validator=None,  # Пока None
            db_session=self._db_session,
        )

        return await interactor(
            actor_uuid=removed_by,
            team_uuid=team_uuid,
            user_uuid=user_uuid,
        )

    async def transfer_team_ownership(
        self,
        team_uuid: UUID,
        new_owner_uuid: UUID,
        current_owner_uuid: UUID,
    ) -> bool:
        """Передать владение командой"""

        interactor = TransferOwnershipInteractor(
            team_repo=self._team_repo,
            user_repo=self._user_repo,
            permission_validator=None,  # Пока None
            db_session=self._db_session,
        )

        return await interactor(
            actor_uuid=current_owner_uuid,
            team_uuid=team_uuid,
            new_owner_uuid=new_owner_uuid,
        )

    async def generate_team_invite_code(
        self,
        team_uuid: UUID,
        created_by: UUID,
    ) -> str:
        """Создать код приглашения в команду"""

        interactor = GenerateInviteCodeInteractor(
            team_repo=self._team_repo,
            user_repo=self._user_repo,
            permission_validator=None,  # Пока None
        )

        return await interactor(
            actor_uuid=created_by,
            team_uuid=team_uuid,
        )

    async def join_team_by_code(
        self,
        user_uuid: UUID,
        invite_code: str,
    ) -> bool:
        """Присоединиться к команде по коду приглашения"""

        interactor = JoinTeamByInviteCodeInteractor(
            team_repo=self._team_repo,
            user_repo=self._user_repo,
            db_session=self._db_session,
        )

        return await interactor(
            user_uuid=user_uuid,
            invite_code=invite_code,
        )
