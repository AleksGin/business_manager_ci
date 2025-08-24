from typing import (
    Dict,
    List,
    Optional,
)
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from src.core.dependencies import (
    CurrentUserDep,
    SessionDep,
    TeamRepoDep,
    UserRepoDep,
    UUIDGeneratorDep,
)
from src.teams.interactors import (
    CreateTeamDTO,
    CreateTeamInteractor,
    DeleteTeamInteractor,
    GetTeamInteractor,
    QueryTeamsInteractor,
    UpdateTeamInteractor,
)
from src.teams.schemas.team import (
    TeamCreate,
    TeamResponse,
    TeamUpdate,
    TeamWithMembers,
)

router = APIRouter()


@router.post(
    "/",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_team(
    team_data: TeamCreate,
    current_user: CurrentUserDep,
    session: SessionDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
    uuid_generator: UUIDGeneratorDep,
) -> TeamResponse:
    """Создать новую команду"""

    dto = CreateTeamDTO(
        name=team_data.name,
        description=team_data.description,
        owner_uuid=current_user.uuid,  # Создатель становится владельцем
    )

    interactor = CreateTeamInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
        uuid_generator=uuid_generator,
        db_session=session,
    )

    try:
        team = await interactor(
            actor_uuid=current_user.uuid,
            dto=dto,
        )
        return TeamResponse.model_validate(team)

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


@router.get(
    "/",
    response_model=List[TeamResponse],
    status_code=status.HTTP_200_OK,
)
async def list_teams(
    current_user: CurrentUserDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    owner_uuid: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> List[TeamResponse]:
    """Получить список команд"""

    interactor = QueryTeamsInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        teams = await interactor(
            actor_uuid=current_user.uuid,
            limit=limit,
            offset=offset,
            owner_uuid=owner_uuid,
            search_query=search,
        )
        return [TeamResponse.model_validate(team) for team in teams]

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


@router.get(
    "/{team_uuid}",
    response_model=TeamResponse,
    status_code=status.HTTP_200_OK,
)
async def get_team(
    team_uuid: UUID,
    current_user: CurrentUserDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> TeamResponse:
    """Получить команду по UUID"""

    interactor = GetTeamInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        team = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            with_members=False,
        )

        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Команда не найдена",
            )

        return TeamResponse.model_validate(team)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{team_uuid}/with-members",
    response_model=TeamWithMembers,
    status_code=status.HTTP_200_OK,
)
async def get_team_with_members(
    team_uuid: UUID,
    current_user: CurrentUserDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> TeamWithMembers:
    """Получить команду с участниками"""

    interactor = GetTeamInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        team = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            with_members=True,
        )

        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Команда не найдена",
            )

        return TeamWithMembers.model_validate(team)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/{team_uuid}",
    response_model=TeamResponse,
    status_code=status.HTTP_200_OK,
)
async def update_team(
    team_uuid: UUID,
    update_data: TeamUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> TeamResponse:
    """Обновить команду"""

    interactor = UpdateTeamInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        team = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            update_data=update_data,
        )

        return TeamResponse.model_validate(team)

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
    "/{team_uuid}",
    status_code=status.HTTP_200_OK,
)
async def delete_team(
    team_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    team_repo: TeamRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Удалить команду"""

    interactor = DeleteTeamInteractor(
        team_repo=team_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Команда не найдена",
            )

        return {"message": "Команда успешно удалена"}

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
