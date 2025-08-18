
from typing import (
    Any,
    Dict,
    List,
)
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from core.dependencies import (
    CurrentUserDep,
    SessionDep,
    TeamRepoDep,
    UserRepoDep,
)
from teams.interactors.team_membership_interactors import (
    AddTeamMemberInteractor,
    GenerateInviteCodeInteractor,
    GetTeamMembersInteractor,
    RemoveTeamMemberInteractor,
    TransferOwnershipInteractor,
)
from teams.schemas.team import (
    TeamInvite,
    TeamRemoveMember,
    TeamTransferOwnership,
    TeamInviteResponse,
)
from users.schemas import UserInTeam

router = APIRouter()


@router.get(
    "/{team_uuid}/members",
    response_model=List[UserInTeam],
    status_code=status.HTTP_200_OK,
)
async def get_team_members(
    team_uuid: UUID,
    current_user: CurrentUserDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> List[UserInTeam]:
    """Получить список участников команды"""

    interactor = GetTeamMembersInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        members = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
        )
        return [UserInTeam.model_validate(member) for member in members]

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{team_uuid}/members",
    status_code=status.HTTP_200_OK,
)
async def add_team_member(
    team_uuid: UUID,
    member_data: TeamInvite,
    current_user: CurrentUserDep,
    session: SessionDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Добавить участника в команду"""

    # Определить UUID пользователя для добавления
    if member_data.user_uuid:
        target_user_uuid = member_data.user_uuid
    elif member_data.user_email:
        # Найти пользователя по email
        target_user = await user_repo.get_by_email(member_data.user_email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с email {member_data.user_email} не найден",
            )
        target_user_uuid = target_user.uuid
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать user_uuid или user_email",
        )

    interactor = AddTeamMemberInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            user_uuid=target_user_uuid,
        )

        if result:
            return {"message": "Участник успешно добавлен в команду"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось добавить участника",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.delete(
    "/{team_uuid}/members",
    status_code=status.HTTP_200_OK,
)
async def remove_team_member(
    team_uuid: UUID,
    member_data: TeamRemoveMember,
    current_user: CurrentUserDep,
    session: SessionDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Удалить участника из команды"""

    interactor = RemoveTeamMemberInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            user_uuid=member_data.user_uuid,
        )

        if result:
            return {"message": "Участник успешно удален из команды"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось удалить участника",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{team_uuid}/transfer-ownership",
    status_code=status.HTTP_200_OK,
)
async def transfer_ownership(
    team_uuid: UUID,
    transfer_data: TeamTransferOwnership,
    current_user: CurrentUserDep,
    session: SessionDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Передать владение командой"""

    interactor = TransferOwnershipInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            new_owner_uuid=transfer_data.new_owner_uuid,
        )

        if result:
            return {"message": "Владение командой успешно передано"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось передать владение",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{team_uuid}/generate-invite",
    status_code=status.HTTP_200_OK,
)
async def generate_invite_code(
    team_uuid: UUID,
    current_user: CurrentUserDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> TeamInviteResponse:
    """Сгенерировать код приглашения в команду"""

    interactor = GenerateInviteCodeInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        invite_code = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
        )

        return TeamInviteResponse(
            message="Код приглашения сгенерирован",
            invite_code=invite_code,
            expires_in_hours=24,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{team_uuid}/leave",
    status_code=status.HTTP_200_OK,
)
async def leave_team(
    team_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Покинуть команду"""

    interactor = RemoveTeamMemberInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            user_uuid=current_user.uuid,  # Удаляем себя
        )

        if result:
            return {"message": "Вы успешно покинули команду"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось покинуть команду",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
