from datetime import datetime
from typing import (
    Any,
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
    MeetingRepoDep,
    SessionDep,
    TeamRepoDep,
    UUIDGeneratorDep,
    UserRepoDep,
)
from src.meetings.interactors import (
    CreateMeetingDTO,
    CreateMeetingInteractor,
    DeleteMeetingInteractor,
    GetMeetingInteractor,
    GetMeetingStatsInteractor,
    ManageMeetingParticipantsInteractor,
    QueryMeetingsInteractor,
    UpdateMeetingInteractor,
)
from src.meetings.schemas.meeting import (
    MeetingAddParticipants,
    MeetingCreate,
    MeetingRemoveParticipants,
    MeetingResponse,
    MeetingUpdate,
    MeetingWithDetails,
)

router = APIRouter()


@router.post(
    "/",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_meeting(
    meeting_data: MeetingCreate,
    current_user: CurrentUserDep,
    session: SessionDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    team_repo: TeamRepoDep,
    uuid_generator: UUIDGeneratorDep,
) -> MeetingResponse:
    """Создать новую встречу"""

    dto = CreateMeetingDTO(
        title=meeting_data.title,
        description=meeting_data.description,
        date_time=meeting_data.date_time,
        team_uuid=meeting_data.team_uuid,
        creator_uuid=current_user.uuid,
        participants_uuids=meeting_data.participants_uuids,
    )

    interactor = CreateMeetingInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        team_repo=team_repo,
        permission_validator=None,
        uuid_generator=uuid_generator,
        db_session=session,
    )

    try:
        meeting = await interactor(
            actor_uuid=current_user.uuid,
            dto=dto,
        )
        return MeetingResponse.model_validate(meeting)

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
    response_model=List[MeetingResponse],
    status_code=status.HTTP_200_OK,
)
async def list_meetings(
    current_user: CurrentUserDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    team_uuid: Optional[UUID] = Query(default=None),
    creator_uuid: Optional[UUID] = Query(default=None),
    participant_uuid: Optional[UUID] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    upcoming_only: bool = Query(
        default=False, description="Показать только предстоящие встречи"
    ),
) -> List[MeetingResponse]:
    """Получить список встреч"""

    interactor = QueryMeetingsInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        meetings = await interactor(
            actor_uuid=current_user.uuid,
            limit=limit,
            offset=offset,
            team_uuid=team_uuid,
            creator_uuid=creator_uuid,
            participant_uuid=participant_uuid,
            date_from=date_from,
            date_to=date_to,
            upcoming_only=upcoming_only,
        )
        return [MeetingResponse.model_validate(meeting) for meeting in meetings]

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
    "/by-date",
    response_model=List[MeetingResponse],
    status_code=status.HTTP_200_OK,
)
async def get_meetings_by_date(
    current_user: CurrentUserDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    target_date: datetime = Query(description="Дата для поиска встреч"),
    team_uuid: Optional[UUID] = Query(default=None),
    participant_uuid: Optional[UUID] = Query(default=None),
) -> List[MeetingResponse]:
    """Получить встречи на конкретную дату"""

    interactor = QueryMeetingsInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        meetings = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            participant_uuid=participant_uuid,
            by_date=target_date,
        )
        return [MeetingResponse.model_validate(meeting) for meeting in meetings]

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
    "/{meeting_uuid}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_meeting(
    meeting_uuid: UUID,
    current_user: CurrentUserDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> MeetingResponse:
    """Получить встречу по UUID"""

    interactor = GetMeetingInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        meeting = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            meeting_uuid=meeting_uuid,
            with_participants=False,
        )

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Встреча не найдена",
            )

        return MeetingResponse.model_validate(meeting)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{meeting_uuid}/details",
    response_model=MeetingWithDetails,
    status_code=status.HTTP_200_OK,
)
async def get_meeting_with_details(
    meeting_uuid: UUID,
    current_user: CurrentUserDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> MeetingWithDetails:
    """Получить встречу с участниками"""

    interactor = GetMeetingInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        meeting = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            meeting_uuid=meeting_uuid,
            with_participants=True,
        )

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Встреча не найдена",
            )

        return MeetingWithDetails.model_validate(meeting)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/{meeting_uuid}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
)
async def update_meeting(
    meeting_uuid: UUID,
    update_data: MeetingUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> MeetingResponse:
    """Обновить встречу"""

    interactor = UpdateMeetingInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        meeting = await interactor(
            actor_uuid=current_user.uuid,
            meeting_uuid=meeting_uuid,
            update_data=update_data,
        )

        return MeetingResponse.model_validate(meeting)

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
    "/{meeting_uuid}",
    status_code=status.HTTP_200_OK,
)
async def delete_meeting(
    meeting_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Удалить встречу"""

    interactor = DeleteMeetingInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            meeting_uuid=meeting_uuid,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Встреча не найдена",
            )

        return {"message": "Встреча успешно удалена"}

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{meeting_uuid}/participants",
    status_code=status.HTTP_200_OK,
)
async def add_meeting_participants(
    meeting_uuid: UUID,
    participants_data: MeetingAddParticipants,
    current_user: CurrentUserDep,
    session: SessionDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Добавить участников во встречу"""

    interactor = ManageMeetingParticipantsInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor.add_participants(
            actor_uuid=current_user.uuid,
            meeting_uuid=meeting_uuid,
            participant_uuids=participants_data.participants_uuids,
        )

        if result:
            return {"message": "Участники успешно добавлены во встречу"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось добавить участников",
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
    "/{meeting_uuid}/participants",
    status_code=status.HTTP_200_OK,
)
async def remove_meeting_participants(
    meeting_uuid: UUID,
    participants_data: MeetingRemoveParticipants,
    current_user: CurrentUserDep,
    session: SessionDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Удалить участников из встречи"""

    interactor = ManageMeetingParticipantsInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor.remove_participants(
            actor_uuid=current_user.uuid,
            meeting_uuid=meeting_uuid,
            participant_uuids=participants_data.participants_uuids,
        )

        if result:
            return {"message": "Участники успешно удалены из встречи"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось удалить участников",
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
    "/{meeting_uuid}/leave",
    status_code=status.HTTP_200_OK,
)
async def leave_meeting(
    meeting_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Покинуть встречу (удалить себя из участников)"""

    interactor = ManageMeetingParticipantsInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor.remove_participants(
            actor_uuid=current_user.uuid,
            meeting_uuid=meeting_uuid,
            participant_uuids=[current_user.uuid],  # Удаляем себя
        )

        if result:
            return {"message": "Вы успешно покинули встречу"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы не являетесь участником этой встречи",
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


@router.get(
    "/stats/overview",
    status_code=status.HTTP_200_OK,
)
async def get_meeting_stats(
    current_user: CurrentUserDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    user_uuid: Optional[UUID] = Query(default=None),
    team_uuid: Optional[UUID] = Query(default=None),
) -> Dict[str, Any]:
    """Получить статистику встреч"""

    interactor = GetMeetingStatsInteractor(
        meeting_repo=meeting_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        stats = await interactor(
            actor_uuid=current_user.uuid,
            user_uuid=user_uuid,
            team_uuid=team_uuid,
        )

        return stats

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
